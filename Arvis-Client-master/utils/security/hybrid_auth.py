"""
Hybrid Authentication Manager
Гибридный менеджер аутентификации (локальная + удаленная)
"""

from datetime import datetime
from typing import Optional, Tuple

from config.config import Config
from utils.logger import ModuleLogger
from utils.security.auth import AuthManager as LocalAuthManager
from utils.security.auth import User
from utils.security.client_api import ArvisClientAPI, get_client_api
from utils.security.rbac import Role


class HybridAuthManager:
    """
    Гибридный менеджер аутентификации, который поддерживает как локальную,
    так и удаленную аутентификацию с возможностью отката к локальной,
    если удаленный сервер недоступен.
    """

    def __init__(self, config: Optional[Config] = None):
        """
        Инициализация гибридного менеджера аутентификации.

        Args:
            config: Объект конфигурации.
        """
        self.logger = ModuleLogger("HybridAuthManager")
        self.config = config or Config()

        self.use_remote = self.config.get("security.auth.use_remote_server", False)
        self.strict_server_mode = self.config.get("security.auth.strict_server_mode", False)

        self.client_api: Optional[ArvisClientAPI] = None
        self.local_auth: Optional[LocalAuthManager] = None

        if self.use_remote:
            self.client_api = get_client_api(self.config)
            if self.client_api:
                if self.client_api.check_connection():
                    self.logger.info("✓ Remote authentication is active.")
                else:
                    self.logger.warning("⚠ Remote server is configured but unreachable.")
                    if self.strict_server_mode:
                        self.logger.error("✗ CRITICAL: Strict server mode is ON, but the server is unavailable.")
                        raise ConnectionError("Server unavailable in strict mode.")
                    self.logger.info("→ Falling back to local authentication mode.")
                    self.client_api = None # Отключаем API, если сервер недоступен
            else:
                self.logger.warning("⚠ Remote authentication is enabled in config, but client API could not be initialized.")

        if not self.strict_server_mode:
            self.local_auth = LocalAuthManager(self.config)
            self.logger.info("Local authentication is available as a fallback.")
        else:
            self.logger.info("Strict server mode is ON: local authentication is disabled.")

        self.current_user: Optional[User] = None

    def authenticate(
        self, username: str, password: str, totp_code: Optional[str] = None
    ) -> Tuple[bool, Optional[str], Optional[User]]:
        """
        Аутентифицирует пользователя. Сначала пытается через удаленный сервер,
        затем, если не удалось, через локальную базу данных.

        Args:
            username: Имя пользователя.
            password: Пароль.
            totp_code: Код двухфакторной аутентификации (пока не используется).

        Returns:
            Кортеж (успех, сообщение_об_ошибке, объект_пользователя).
        """
        # 1. Попытка удаленной аутентификации
        if self.client_api:
            try:
                result = self.client_api.login(username, password)
                if result.get("success"):
                    user_data = result.get("user", {})
                    user = self._create_user_from_api(user_data)
                    self.current_user = user
                    self.logger.info(f"✓ Remote authentication successful for '{username}'.")
                    return True, None, user
                
                error_msg = result.get("detail", "Invalid credentials.")
                self.logger.warning(f"Remote authentication failed for '{username}': {error_msg}")
                # Если строгий режим, не пытаемся использовать локальную аутентификацию
                if self.strict_server_mode:
                    return False, error_msg, None
                self.logger.info("→ Falling back to local authentication.")

            except Exception as e:
                self.logger.error(f"An error occurred during remote authentication: {e}")
                if self.strict_server_mode:
                    return False, "A server error occurred.", None
                self.logger.info("→ Falling back to local authentication.")

        # 2. Попытка локальной аутентификации (если не строгий режим)
        if not self.local_auth:
            return False, "Server unavailable and local authentication is disabled.", None

        try:
            session = self.local_auth.authenticate(username, password)
            if session:
                user = self.local_auth.get_user_by_id(session.user_id)
                if user:
                    self.current_user = user
                    self.logger.info(f"✓ Local authentication successful for '{username}'.")
                    return True, None, user
                return False, "User not found for the created session.", None
            
            return False, "Invalid username or password.", None

        except PermissionError as e:
            self.logger.warning(f"Local authentication failed for '{username}': {e}")
            return False, str(e), None
        except Exception as e:
            self.logger.error(f"An unexpected error occurred during local authentication: {e}")
            return False, str(e), None

    def logout(self) -> bool:
        """Выход текущего пользователя из системы."""
        if self.client_api and self.client_api.is_logged_in():
            self.client_api.logout()
        
        if self.current_user and self.local_auth:
            self.local_auth.logout(self.current_user.user_id)

        self.current_user = None
        self.logger.info("✓ User logged out, local and remote sessions cleared.")
        return True

    def create_user(self, username: str, password: str, email: str = "", role: str = "user") -> Tuple[bool, str]:
        """
        Создает нового пользователя. В гибридном режиме создание возможно только через сервер.
        В локальном режиме - локально.
        """
        # 1. Попытка создания через сервер
        if self.client_api:
            self.logger.info(f"Attempting to register user '{username}' on the server.")
            # Используем обновлённый API с email как optional
            result = self.client_api.register(username, password, email if email else None)
            if result.get("success"):
                user_id = result.get('user_id', 'N/A')
                self.logger.info(f"✓ User '{username}' (ID: {user_id}) registered successfully on the server.")
                return True, f"User '{username}' created successfully."
            
            error_msg = result.get("detail", "Server registration failed.")
            self.logger.error(f"✗ Failed to register user on server: {error_msg}")
            return False, error_msg

        # 2. Попытка создания локально (если разрешено)
        if self.local_auth:
            self.logger.info(f"Server not available. Attempting to create user '{username}' locally.")
            try:
                role_enum = Role[role.upper()]
                # The create_user method in local_auth does not take email as an argument.
                user = self.local_auth.create_user(username, password, role_enum)
                if user:
                    self.logger.info(f"✓ User '{username}' created locally.")
                    # We might want to update the email separately if the local_auth manager supports it.
                    # self.local_auth.update_user(user.user_id, email=email)
                    return True, f"User '{username}' created locally."
                return False, "Failed to create user locally."
            except Exception as e:
                self.logger.error(f"Error creating user locally: {e}")
                return False, str(e)

        return False, "No authentication method available to create a user."

    def get_current_user(self) -> Optional[User]:
        """Возвращает текущего аутентифицированного пользователя."""
        # Если есть удаленный клиент, попробуем обновить инфо о пользователе
        if self.client_api and self.client_api.is_logged_in():
            api_user_info = self.client_api.get_current_user()
            if api_user_info:
                self.current_user = self._create_user_from_api(api_user_info)
        return self.current_user

    def _create_user_from_api(self, api_data: dict) -> User:
        """
        Создает объект User из данных, полученных от API.
        """
        role_str = api_data.get("role", "user")
        try:
            # На сервере может быть is_admin, а не role
            if api_data.get('is_admin'):
                role = Role.ADMIN
            else:
                role = Role[role_str.upper()]
        except KeyError:
            self.logger.warning(f"Unknown role '{role_str}' from server. Defaulting to USER.")
            role = Role.USER

        # Преобразование created_at в datetime, если возможно
        created_at_str = api_data.get("created_at")
        if created_at_str:
            try:
                # Попытка распарсить дату в формате ISO
                created_at = datetime.fromisoformat(created_at_str.replace("Z", "+00:00"))
            except (ValueError, TypeError):
                created_at = datetime.utcnow()
        else:
            created_at = datetime.utcnow()

        return User(
            user_id=api_data.get("user_id", "remote_user"),
            username=api_data.get("username", "Unknown"),
            role=role,
            is_active=api_data.get("is_active", True),
            password_hash="",  # Пароль не хранится для удаленных пользователей
            salt="",
            created_at=created_at,
            last_login=datetime.utcnow(),
            require_2fa=False, # 2FA пока не поддерживается в этой логике
        )

# Global instance
_hybrid_auth_manager: Optional[HybridAuthManager] = None


def get_hybrid_auth_manager(config: Optional[Config] = None) -> HybridAuthManager:
    """Возвращает или создает глобальный экземпляр HybridAuthManager."""
    global _hybrid_auth_manager
    if _hybrid_auth_manager is None:
        _hybrid_auth_manager = HybridAuthManager(config)
    return _hybrid_auth_manager
