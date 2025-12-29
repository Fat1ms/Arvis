"""
Authentication system for Arvis
Система аутентификации пользователей
"""

import hashlib
import hmac
import os
import secrets
import time
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Optional

from utils.logger import ModuleLogger
from utils.security.rbac import Role

# Lazy import для избежания циклических зависимостей
_storage = None


def _get_storage():
    global _storage
    if _storage is None:
        from utils.security.storage import get_storage

        _storage = get_storage()
    return _storage


@dataclass
class User:
    """Модель пользователя"""

    user_id: str
    username: str
    role: Role
    password_hash: str
    salt: str
    created_at: datetime
    last_login: Optional[datetime] = None
    is_active: bool = True
    require_2fa: bool = False
    totp_secret: Optional[str] = None
    backup_codes: Optional[str] = None  # JSON string of hashed codes (Phase 2 Day 5)
    two_factor_setup_at: Optional[datetime] = None  # When 2FA was enabled (Phase 2 Day 5)


@dataclass
class Session:
    """Модель сессии"""

    session_id: str
    user_id: str
    created_at: datetime
    expires_at: datetime
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None


class AuthManager:
    """Менеджер аутентификации"""

    # Настройки по умолчанию
    DEFAULT_SESSION_TIMEOUT = 3600  # 1 час
    DEFAULT_PASSWORD_MIN_LENGTH = 8
    DEFAULT_MAX_LOGIN_ATTEMPTS = 5
    DEFAULT_LOCKOUT_DURATION = 300  # 5 минут

    def __init__(self, config=None):
        self.logger = ModuleLogger("AuthManager")
        self.config = config or {}

        # Настройки
        self.session_timeout = self.config.get("auth.session_timeout", self.DEFAULT_SESSION_TIMEOUT)
        self.password_min_length = self.config.get("auth.password_min_length", self.DEFAULT_PASSWORD_MIN_LENGTH)
        self.max_login_attempts = self.config.get("auth.max_login_attempts", self.DEFAULT_MAX_LOGIN_ATTEMPTS)
        self.lockout_duration = self.config.get("auth.lockout_duration", self.DEFAULT_LOCKOUT_DURATION)

        # Хранилище (v1.5.0: SQLite)
        self.use_storage = self.config.get("auth.use_storage", True)
        self.storage = _get_storage() if self.use_storage else None

        # Временные хранилища (fallback, если хранилище выключено)
        self.users: Dict[str, User] = {}
        self.sessions: Dict[str, Session] = {}
        self.login_attempts: Dict[str, list] = {}  # username -> [timestamps]

        # Создаём админа по умолчанию (если нет пользователей)
        self._init_default_admin()

    def _init_default_admin(self):
        """Создать админа по умолчанию"""
        # Проверяем наличие пользователей
        if self.storage:
            users = self.storage.list_users()
            if users:
                self.logger.info(f"Found {len(users)} existing users in database")
                return
        elif self.users:
            return

        # Если нет пользователей - создаём админа
        if not self.storage and not self.users:
            # Генерируем случайный пароль для первого запуска
            default_password = secrets.token_urlsafe(12)
            self.logger.warning(f"Creating default admin user. " f"Password: {default_password} (SAVE THIS!)")

            admin = self.create_user(username="admin", password=default_password, role=Role.ADMIN)

            # Сохраняем пароль в файл для первого входа
            self._save_default_password(default_password)

    def _save_default_password(self, password: str):
        """Сохранить пароль по умолчанию в файл"""
        try:
            temp_file = Path("data") / ".admin_password.txt"
            temp_file.parent.mkdir(parents=True, exist_ok=True)

            with open(temp_file, "w") as f:
                f.write(f"Default Admin Password: {password}\n")
                f.write("IMPORTANT: Change this password immediately!\n")
                f.write("This file will be deleted after first login.\n")

            # Устанавливаем права только на чтение для владельца (Unix-like)
            if hasattr(os, "chmod"):
                os.chmod(temp_file, 0o600)

        except Exception as e:
            self.logger.error(f"Failed to save default password: {e}")

    def _hash_password(self, password: str, salt: Optional[str] = None) -> tuple[str, str]:
        """Хэшировать пароль с солью

        Returns:
            (password_hash, salt)
        """
        if salt is None:
            salt = secrets.token_hex(32)

        # Используем PBKDF2 с SHA-256 (100000 итераций)
        password_hash = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), 100000).hex()

        return password_hash, salt

    def _verify_password(self, password: str, password_hash: str, salt: str) -> bool:
        """Проверить пароль"""
        computed_hash, _ = self._hash_password(password, salt)
        return hmac.compare_digest(computed_hash, password_hash)

    def validate_password_strength(self, password: str) -> tuple[bool, str]:
        """Проверить надёжность пароля

        Returns:
            (is_valid, error_message)
        """
        if len(password) < self.password_min_length:
            return False, f"Пароль должен быть не менее {self.password_min_length} символов"

        # Проверяем наличие разных типов символов
        has_upper = any(c.isupper() for c in password)
        has_lower = any(c.islower() for c in password)
        has_digit = any(c.isdigit() for c in password)
        has_special = any(c in "!@#$%^&*()_+-=[]{}|;:,.<>?" for c in password)

        strength_checks = sum([has_upper, has_lower, has_digit, has_special])

        if strength_checks < 3:
            return False, (
                "Пароль должен содержать минимум 3 из: " "заглавные буквы, строчные буквы, цифры, спецсимволы"
            )

        return True, ""

    def create_user(self, username: str, password: str, role: Role = Role.USER) -> User:
        """Создать нового пользователя"""
        # Проверяем, не существует ли пользователь
        if self.storage:
            existing = self.storage.get_user(username)
            if existing:
                raise ValueError(f"User '{username}' already exists")
        elif username in self.users:
            raise ValueError(f"User '{username}' already exists")

        # Проверяем надёжность пароля
        is_valid, error = self.validate_password_strength(password)
        if not is_valid:
            raise ValueError(error)

        # Хэшируем пароль
        password_hash, salt = self._hash_password(password)

        # Создаём пользователя
        user = User(
            user_id=secrets.token_urlsafe(16),
            username=username,
            role=role,
            password_hash=password_hash,
            salt=salt,
            created_at=datetime.now(),
        )

        # Сохраняем в хранилище или память
        if self.storage:
            self.storage.save_user(user)
        else:
            self.users[username] = user

        self.logger.info(f"Created user '{username}' with role {role.value}")

        return user

    def authenticate(self, username: str, password: str, ip_address: Optional[str] = None) -> Optional[Session]:
        """Аутентифицировать пользователя

        Returns:
            Session если успешно, None если неудачно
        """
        # Проверяем блокировку
        if self._is_locked_out(username):
            self.logger.warning(f"Login attempt for locked user '{username}'")
            raise PermissionError(f"Account is locked due to too many failed attempts. " f"Try again later.")

        # Получаем пользователя из хранилища или памяти
        if self.storage:
            user = self.storage.get_user(username)
        else:
            user = self.users.get(username)

        if user is None:
            self._record_failed_login(username)
            return None

        # Проверяем активность
        if not user.is_active:
            self.logger.warning(f"Login attempt for inactive user '{username}'")
            return None

        # Проверяем пароль
        if not self._verify_password(password, user.password_hash, user.salt):
            self._record_failed_login(username)
            return None

        # TODO: Проверка 2FA если включена
        if user.require_2fa:
            # Пока пропускаем, реализуем позже
            pass

        # Сброс счётчика неудачных попыток
        self.login_attempts.pop(username, None)

        # Создаём сессию
        session = self._create_session(user, ip_address)

        # Обновляем время последнего входа
        user.last_login = datetime.now()

        self.logger.info(f"User '{username}' logged in successfully")

        return session

    def _create_session(self, user: User, ip_address: Optional[str] = None) -> Session:
        """Создать новую сессию"""
        session = Session(
            session_id=secrets.token_urlsafe(32),
            user_id=user.user_id,
            created_at=datetime.now(),
            expires_at=datetime.now() + timedelta(seconds=self.session_timeout),
            ip_address=ip_address,
        )

        # Сохраняем в хранилище или память
        if self.storage:
            self.storage.save_session(session)
        else:
            self.sessions[session.session_id] = session

        return session

    def validate_session(self, session_id: str) -> Optional[User]:
        """Проверить валидность сессии

        Returns:
            User если сессия валидна, None если нет
        """
        # Получаем сессию из хранилища или памяти
        if self.storage:
            session = self.storage.get_session(session_id)
        else:
            session = self.sessions.get(session_id)

        if session is None:
            return None

        # Проверяем срок действия
        if datetime.now() > session.expires_at:
            self.logger.debug(f"Session {session_id} expired")
            if self.storage:
                self.storage.delete_session(session_id)
            else:
                del self.sessions[session_id]
            return None

        # Получаем пользователя из хранилища или памяти
        if self.storage:
            user = self.storage.get_user_by_id(session.user_id)
        else:
            user = next((u for u in self.users.values() if u.user_id == session.user_id), None)

        if user is None or not user.is_active:
            return None

        return user

    def logout(self, session_id: str):
        """Завершить сессию"""
        if session_id in self.sessions:
            del self.sessions[session_id]
            self.logger.debug(f"Session {session_id} logged out")

    def change_password(self, username: str, old_password: str, new_password: str) -> bool:
        """Изменить пароль пользователя"""
        # Получаем пользователя из storage или in-memory словаря
        if self.storage:
            user = self.storage.get_user(username)
        else:
            user = self.users.get(username)

        if user is None:
            return False

        # Проверяем старый пароль
        if not self._verify_password(old_password, user.password_hash, user.salt):
            return False

        # Проверяем надёжность нового пароля
        is_valid, error = self.validate_password_strength(new_password)
        if not is_valid:
            raise ValueError(error)

        # Хэшируем новый пароль
        new_hash, new_salt = self._hash_password(new_password)

        user.password_hash = new_hash
        user.salt = new_salt

        # Сохраняем изменения
        if self.storage:
            self.storage.save_user(user)
        else:
            self.users[username] = user

        self.logger.info(f"Password changed for user '{username}'")
        return True

    def _record_failed_login(self, username: str):
        """Записать неудачную попытку входа"""
        if username not in self.login_attempts:
            self.login_attempts[username] = []

        self.login_attempts[username].append(time.time())

        # Очищаем старые попытки (старше lockout_duration)
        cutoff = time.time() - self.lockout_duration
        self.login_attempts[username] = [ts for ts in self.login_attempts[username] if ts > cutoff]

    def _is_locked_out(self, username: str) -> bool:
        """Проверить, заблокирован ли пользователь"""
        attempts = self.login_attempts.get(username, [])

        # Очищаем старые попытки
        cutoff = time.time() - self.lockout_duration
        recent_attempts = [ts for ts in attempts if ts > cutoff]

        return len(recent_attempts) >= self.max_login_attempts

    def cleanup_expired_sessions(self):
        """Очистить истёкшие сессии"""
        now = datetime.now()
        expired = [sid for sid, session in self.sessions.items() if now > session.expires_at]

        for sid in expired:
            del self.sessions[sid]

        if expired:
            self.logger.debug(f"Cleaned up {len(expired)} expired sessions")

    def get_user_by_id(self, user_id: str) -> Optional[User]:
        """Get user by ID"""
        if self.storage:
            return self.storage.get_user_by_id(user_id)
        else:
            return next((u for u in self.users.values() if u.user_id == user_id), None)

    def list_users(self) -> list:
        """List all users"""
        if self.storage:
            return self.storage.list_users()
        else:
            return list(self.users.values())

    def update_user(self, user_id: str, **kwargs) -> bool:
        """Update user fields"""
        user = self.get_user_by_id(user_id)
        if not user:
            return False

        # Update fields
        for key, value in kwargs.items():
            if hasattr(user, key):
                setattr(user, key, value)

        # Save changes
        if self.storage:
            self.storage.save_user(user)
        else:
            # Find and update in dict
            for username, u in self.users.items():
                if u.user_id == user_id:
                    self.users[username] = user
                    break

        return True

    def delete_user(self, user_id: str) -> bool:
        """Delete user"""
        if self.storage:
            return self.storage.delete_user(user_id)
        else:
            # Find and delete from dict
            for username, user in list(self.users.items()):
                if user.user_id == user_id:
                    del self.users[username]
                    return True
            return False


# Глобальный экземпляр менеджера аутентификации
_auth_manager: Optional[AuthManager] = None


def get_auth_manager(config=None) -> AuthManager:
    """Получить глобальный экземпляр менеджера аутентификации"""
    global _auth_manager
    if _auth_manager is None:
        _auth_manager = AuthManager(config)
    return _auth_manager
