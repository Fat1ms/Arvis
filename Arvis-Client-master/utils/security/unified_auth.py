"""
Unified authentication manager
Унифицированный менеджер аутентификации (локальный или серверный)
"""

from typing import Optional

from config import config
from utils.logger import ModuleLogger


class UnifiedAuthManager:
    """
    Unified authentication manager that switches between:
    - Local SQLite storage (legacy)
    - Remote authentication server (new)
    """

    def __init__(self, config_obj=None):
        self.logger = ModuleLogger("UnifiedAuthManager")
        self.config = config_obj or config

        # Определяем режим
        self.mode = self.config.get("auth.mode", "local")
        self.server_url = self.config.get("auth.server_url", None)
        self.fallback_to_local = self.config.get("auth.fallback_to_local", True)

        self.logger.info(f"Auth mode: {self.mode}")

        # Инициализация клиента
        self._auth_impl = None
        self._init_auth()

    def _init_auth(self):
        """Initialize authentication implementation"""
        if self.mode == "server" and self.server_url:
            try:
                from utils.security.auth_client import AuthClient

                self._auth_impl = AuthClient(self.server_url)

                # Проверяем доступность сервера
                if self._auth_impl.check_connection():
                    self.logger.info(f"Connected to auth server: {self.server_url}")
                else:
                    raise ConnectionError("Server not reachable")

            except Exception as e:
                self.logger.error(f"Failed to connect to server: {e}")

                if self.fallback_to_local:
                    self.logger.warning("Falling back to local authentication")
                    self._init_local_auth()
                else:
                    raise

        else:
            # Локальный режим
            self._init_local_auth()

    def _init_local_auth(self):
        """Initialize local SQLite authentication"""
        from utils.security.auth import AuthManager

        self._auth_impl = AuthManager(self.config)
        self.mode = "local"
        self.logger.info("Using local authentication")

    # === Public API (унифицированный) ===

    def login(self, username: str, password: str) -> Optional[object]:
        """
        Login user

        Returns:
            User object (local) or dict (server) or None
        """
        if self.mode == "server":
            # Серверный режим
            if self._auth_impl.login(username, password):
                return self._auth_impl.get_current_user()
            return None
        else:
            # Локальный режим
            return self._auth_impl.login(username, password)

    def logout(self):
        """Logout current user"""
        if self.mode == "server":
            return self._auth_impl.logout()
        else:
            # В локальном режиме logout не нужен (sessionless)
            return True

    def create_user(self, username: str, password: str, role: str = "user") -> Optional[str]:
        """Create new user (returns user_id)"""
        if self.mode == "server":
            return self._auth_impl.create_user(username, password, role)
        else:
            user_id = self._auth_impl.create_user(username, password, role)
            return user_id

    def get_user(self, username: str) -> Optional[object]:
        """Get user by username"""
        if self.mode == "server":
            # TODO: Implement get_user in AuthClient
            return None
        else:
            return self._auth_impl.get_user(username)

    def list_users(self) -> list:
        """List all users"""
        if self.mode == "server":
            return self._auth_impl.list_users() or []
        else:
            return self._auth_impl.list_users()

    def update_user(self, user_id: str, **kwargs) -> bool:
        """Update user fields"""
        if self.mode == "server":
            return self._auth_impl.update_user(user_id, **kwargs)
        else:
            return self._auth_impl.update_user(user_id, **kwargs)

    def delete_user(self, user_id: str) -> bool:
        """Delete user"""
        if self.mode == "server":
            return self._auth_impl.delete_user(user_id)
        else:
            return self._auth_impl.delete_user(user_id)

    def is_authenticated(self) -> bool:
        """Check if user is authenticated"""
        if self.mode == "server":
            return self._auth_impl.is_authenticated()
        else:
            # В локальном режиме проверяем через current_user (из GUI)
            return True  # Всегда True для совместимости

    def get_mode(self) -> str:
        """Get current auth mode"""
        return self.mode

    def get_server_url(self) -> Optional[str]:
        """Get server URL if in server mode"""
        return self.server_url if self.mode == "server" else None


# Глобальный экземпляр (для совместимости)
_unified_auth_manager = None


def get_unified_auth_manager(config_obj=None) -> UnifiedAuthManager:
    """Get unified auth manager instance"""
    global _unified_auth_manager
    if _unified_auth_manager is None:
        _unified_auth_manager = UnifiedAuthManager(config_obj)
    return _unified_auth_manager
