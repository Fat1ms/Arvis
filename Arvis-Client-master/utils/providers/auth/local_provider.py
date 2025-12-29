"""
Local Auth Provider (SQLite)
Локальный провайдер аутентификации на основе SQLite

Priority: 0 (максимальный приоритет для локальных компонентов)
"""

from typing import Dict, Optional

from config.config import Config
from utils.logger import ModuleLogger
from utils.providers import AuthProvider
from utils.security.auth import AuthManager as LocalAuthManager


class LocalAuthProvider(AuthProvider):
    """
    Провайдер локальной аутентификации через SQLite БД.
    
    Требует:
    - Файл базы данных data/users.db
    - Работает полностью оффлайн
    """

    def __init__(self, config: Config):
        super().__init__("local_sqlite")
        self.config = config
        self.auth_manager: Optional[LocalAuthManager] = None
        self._initialized = False

    def get_priority(self) -> int:
        """Локальные компоненты имеют максимальный приоритет"""
        return 0

    def initialize(self) -> bool:
        """Инициализировать локальный auth"""
        try:
            if self._initialized:
                return self.is_available()

            self.logger.info("Initializing Local SQLite Auth...")
            self.auth_manager = LocalAuthManager(self.config)

            if not self.auth_manager:
                self.logger.error("Failed to create Auth manager")
                self._status.value = "unavailable"
                return False

            self._initialized = True
            self._status.value = "available"
            self.logger.info("✓ Local Auth initialized successfully")
            return True

        except Exception as e:
            self.logger.error(f"Failed to initialize Local Auth: {e}")
            self.set_error(str(e))
            return False

    def is_available(self) -> bool:
        """Проверить доступность локального auth"""
        try:
            if not self._initialized or self.auth_manager is None:
                return False

            # Локальный auth всегда доступен если инициализирован
            return True

        except Exception as e:
            self.logger.debug(f"Local Auth availability check failed: {e}")
            return False

    def authenticate(
        self,
        username: str,
        password: str,
        totp_code: Optional[str] = None,
    ) -> Dict[str, any]:
        """
        Аутентифицировать пользователя локально.
        
        Args:
            username: Имя пользователя
            password: Пароль
            totp_code: TOTP код (если включена 2FA)
            
        Returns:
            Dict с информацией о пользователе:
            {
                "user_id": int,
                "username": str,
                "role": str,
                "token": str (opcional),
            }
        """
        if not self.is_available():
            raise RuntimeError("Local Auth is not available")

        try:
            if self.auth_manager is None:
                raise RuntimeError("Auth manager not initialized")

            # Используем встроенный метод auth manager
            user = self.auth_manager.authenticate(username, password)

            if not user:
                raise RuntimeError("Authentication failed: invalid credentials")

            return {
                "user_id": user.id,
                "username": user.username,
                "role": user.role.value if hasattr(user.role, "value") else str(user.role),
                "email": user.email,
            }

        except Exception as e:
            self.logger.error(f"Local authentication failed: {e}")
            raise RuntimeError(f"Local authentication error: {e}")

    def validate_token(self, token: str) -> bool:
        """
        Проверить токен (для локального auth не требуется, но имплементируем для совместимости).
        
        Args:
            token: Токен для проверки
            
        Returns:
            True если токен валиден
        """
        if not self.is_available():
            return False

        try:
            # Для локального auth токен - просто ID пользователя или сессия
            # В реальной реализации можно использовать JWT
            return bool(token)

        except Exception as e:
            self.logger.debug(f"Token validation failed: {e}")
            return False

    def shutdown(self) -> bool:
        """Завершить работу локального auth"""
        try:
            if self.auth_manager:
                # LocalAuthManager не требует явного завершения
                self.auth_manager = None

            self._initialized = False
            self._status.value = "unavailable"
            self.logger.info("✓ Local Auth shutdown complete")
            return True

        except Exception as e:
            self.logger.error(f"Local Auth shutdown failed: {e}")
            return False
