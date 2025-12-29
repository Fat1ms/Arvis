"""
SQLite storage for RBAC users and sessions
Хранилище пользователей и сессий в SQLite
"""

import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from utils.logger import ModuleLogger
from utils.security.auth import Session, User
from utils.security.rbac import Role


class UserStorage:
    """Хранилище пользователей в SQLite"""

    def __init__(self, db_path: Optional[Path] = None):
        self.logger = ModuleLogger("UserStorage")

        if db_path is None:
            db_path = Path("data") / "users.db"

        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        self._init_database()

    def _init_database(self):
        """Инициализация схемы БД"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            # Таблица пользователей
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS users (
                    user_id TEXT PRIMARY KEY,
                    username TEXT UNIQUE NOT NULL,
                    role TEXT NOT NULL,
                    password_hash TEXT NOT NULL,
                    salt TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    last_login TEXT,
                    is_active INTEGER DEFAULT 1,
                    require_2fa INTEGER DEFAULT 0,
                    totp_secret TEXT,
                    backup_codes TEXT,
                    two_factor_setup_at TEXT
                )
            """
            )

            # Таблица сессий
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS sessions (
                    session_id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    expires_at TEXT NOT NULL,
                    ip_address TEXT,
                    user_agent TEXT,
                    FOREIGN KEY (user_id) REFERENCES users (user_id)
                )
            """
            )

            # Индексы
            cursor.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_users_username
                ON users(username)
            """
            )
            cursor.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_sessions_user_id
                ON sessions(user_id)
            """
            )
            cursor.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_sessions_expires
                ON sessions(expires_at)
            """
            )

            conn.commit()

        self.logger.info(f"Database initialized at {self.db_path}")

    def save_user(self, user: User) -> bool:
        """Сохранить пользователя"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    INSERT OR REPLACE INTO users
                    (user_id, username, role, password_hash, salt, created_at,
                     last_login, is_active, require_2fa, totp_secret)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                    (
                        user.user_id,
                        user.username,
                        user.role.value,
                        user.password_hash,
                        user.salt,
                        user.created_at.isoformat(),
                        user.last_login.isoformat() if user.last_login else None,
                        1 if user.is_active else 0,
                        1 if user.require_2fa else 0,
                        user.totp_secret,
                    ),
                )
                conn.commit()
            return True
        except Exception as e:
            self.logger.error(f"Failed to save user: {e}")
            return False

    def get_user(self, username: str) -> Optional[User]:
        """Получить пользователя по username"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    SELECT user_id, username, role, password_hash, salt,
                           created_at, last_login, is_active, require_2fa, totp_secret,
                           backup_codes, two_factor_setup_at
                    FROM users WHERE username = ?
                """,
                    (username,),
                )
                row = cursor.fetchone()

                if row:
                    return User(
                        user_id=row[0],
                        username=row[1],
                        role=Role(row[2]),
                        password_hash=row[3],
                        salt=row[4],
                        created_at=datetime.fromisoformat(row[5]),
                        last_login=datetime.fromisoformat(row[6]) if row[6] else None,
                        is_active=bool(row[7]),
                        require_2fa=bool(row[8]),
                        totp_secret=row[9],
                        backup_codes=row[10],
                        two_factor_setup_at=datetime.fromisoformat(row[11]) if row[11] else None,
                    )
                return None
        except Exception as e:
            self.logger.error(f"Failed to get user: {e}")
            return None

    def get_user_by_id(self, user_id: str) -> Optional[User]:
        """Получить пользователя по ID"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    SELECT user_id, username, role, password_hash, salt,
                           created_at, last_login, is_active, require_2fa, totp_secret,
                           backup_codes, two_factor_setup_at
                    FROM users WHERE user_id = ?
                """,
                    (user_id,),
                )
                row = cursor.fetchone()

                if row:
                    return User(
                        user_id=row[0],
                        username=row[1],
                        role=Role(row[2]),
                        password_hash=row[3],
                        salt=row[4],
                        created_at=datetime.fromisoformat(row[5]),
                        last_login=datetime.fromisoformat(row[6]) if row[6] else None,
                        is_active=bool(row[7]),
                        require_2fa=bool(row[8]),
                        totp_secret=row[9],
                        backup_codes=row[10],
                        two_factor_setup_at=datetime.fromisoformat(row[11]) if row[11] else None,
                    )
                return None
        except Exception as e:
            self.logger.error(f"Failed to get user by ID: {e}")
            return None

    def list_users(self) -> List[User]:
        """Получить список всех пользователей"""
        users = []
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    SELECT user_id, username, role, password_hash, salt,
                           created_at, last_login, is_active, require_2fa, totp_secret,
                           backup_codes, two_factor_setup_at
                    FROM users
                    ORDER BY created_at
                """
                )

                for row in cursor.fetchall():
                    users.append(
                        User(
                            user_id=row[0],
                            username=row[1],
                            role=Role(row[2]),
                            password_hash=row[3],
                            salt=row[4],
                            created_at=datetime.fromisoformat(row[5]),
                            last_login=datetime.fromisoformat(row[6]) if row[6] else None,
                            is_active=bool(row[7]),
                            require_2fa=bool(row[8]),
                            totp_secret=row[9],
                            backup_codes=row[10],
                            two_factor_setup_at=datetime.fromisoformat(row[11]) if row[11] else None,
                        )
                    )
        except Exception as e:
            self.logger.error(f"Failed to list users: {e}")

        return users

    def delete_user(self, username: str) -> bool:
        """Удалить пользователя"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM users WHERE username = ?", (username,))
                conn.commit()
                return cursor.rowcount > 0
        except Exception as e:
            self.logger.error(f"Failed to delete user: {e}")
            return False

    def save_session(self, session: Session) -> bool:
        """Сохранить сессию"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    INSERT OR REPLACE INTO sessions
                    (session_id, user_id, created_at, expires_at, ip_address, user_agent)
                    VALUES (?, ?, ?, ?, ?, ?)
                """,
                    (
                        session.session_id,
                        session.user_id,
                        session.created_at.isoformat(),
                        session.expires_at.isoformat(),
                        session.ip_address,
                        session.user_agent,
                    ),
                )
                conn.commit()
            return True
        except Exception as e:
            self.logger.error(f"Failed to save session: {e}")
            return False

    def get_session(self, session_id: str) -> Optional[Session]:
        """Получить сессию"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    SELECT session_id, user_id, created_at, expires_at, ip_address, user_agent
                    FROM sessions WHERE session_id = ?
                """,
                    (session_id,),
                )
                row = cursor.fetchone()

                if row:
                    return Session(
                        session_id=row[0],
                        user_id=row[1],
                        created_at=datetime.fromisoformat(row[2]),
                        expires_at=datetime.fromisoformat(row[3]),
                        ip_address=row[4],
                        user_agent=row[5],
                    )
                return None
        except Exception as e:
            self.logger.error(f"Failed to get session: {e}")
            return None

    def delete_session(self, session_id: str) -> bool:
        """Удалить сессию"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM sessions WHERE session_id = ?", (session_id,))
                conn.commit()
                return cursor.rowcount > 0
        except Exception as e:
            self.logger.error(f"Failed to delete session: {e}")
            return False

    def cleanup_expired_sessions(self, now: Optional[datetime] = None) -> int:
        """Удалить истёкшие сессии"""
        if now is None:
            now = datetime.now()

        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    DELETE FROM sessions WHERE expires_at < ?
                """,
                    (now.isoformat(),),
                )
                conn.commit()
                return cursor.rowcount
        except Exception as e:
            self.logger.error(f"Failed to cleanup sessions: {e}")
            return 0

    def get_user_sessions(self, user_id: str) -> List[Session]:
        """Получить все сессии пользователя"""
        sessions = []
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    SELECT session_id, user_id, created_at, expires_at, ip_address, user_agent
                    FROM sessions WHERE user_id = ?
                    ORDER BY created_at DESC
                """,
                    (user_id,),
                )

                for row in cursor.fetchall():
                    sessions.append(
                        Session(
                            session_id=row[0],
                            user_id=row[1],
                            created_at=datetime.fromisoformat(row[2]),
                            expires_at=datetime.fromisoformat(row[3]),
                            ip_address=row[4],
                            user_agent=row[5],
                        )
                    )
        except Exception as e:
            self.logger.error(f"Failed to get user sessions: {e}")

        return sessions

    def enable_two_factor(self, user_id: str, encrypted_secret: str, hashed_backup_codes: str) -> bool:
        """Enable 2FA for user (Phase 2 Day 5)

        Args:
            user_id: User ID
            encrypted_secret: Encrypted TOTP secret
            hashed_backup_codes: JSON string of hashed backup codes

        Returns:
            True if successful
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    UPDATE users
                    SET require_2fa = 1,
                        totp_secret = ?,
                        backup_codes = ?,
                        two_factor_setup_at = ?
                    WHERE user_id = ?
                """,
                    (encrypted_secret, hashed_backup_codes, datetime.now().isoformat(), user_id),
                )
                conn.commit()

                self.logger.info(f"2FA enabled for user: {user_id}")
                return True
        except Exception as e:
            self.logger.error(f"Failed to enable 2FA for user {user_id}: {e}")
            return False

    def disable_two_factor(self, user_id: str) -> bool:
        """Disable 2FA for user (Phase 2 Day 5)

        Args:
            user_id: User ID

        Returns:
            True if successful
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    UPDATE users
                    SET require_2fa = 0,
                        totp_secret = NULL,
                        backup_codes = NULL,
                        two_factor_setup_at = NULL
                    WHERE user_id = ?
                """,
                    (user_id,),
                )
                conn.commit()

                self.logger.info(f"2FA disabled for user: {user_id}")
                return True
        except Exception as e:
            self.logger.error(f"Failed to disable 2FA for user {user_id}: {e}")
            return False

    def get_two_factor_data(self, user_id: str) -> Optional[dict]:
        """Get 2FA data for user (Phase 2 Day 5)

        Args:
            user_id: User ID

        Returns:
            Dict with encrypted_secret and backup_codes, or None
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    SELECT totp_secret, backup_codes, two_factor_setup_at
                    FROM users WHERE user_id = ?
                """,
                    (user_id,),
                )

                row = cursor.fetchone()
                if row and row[0]:  # Has 2FA enabled
                    return {"encrypted_secret": row[0], "backup_codes": row[1], "setup_at": row[2]}
                return None
        except Exception as e:
            self.logger.error(f"Failed to get 2FA data for user {user_id}: {e}")
            return None

    def update_backup_codes(self, user_id: str, hashed_backup_codes: str) -> bool:
        """Update backup codes for user (Phase 2 Day 5)

        Args:
            user_id: User ID
            hashed_backup_codes: JSON string of new hashed backup codes

        Returns:
            True if successful
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    UPDATE users
                    SET backup_codes = ?
                    WHERE user_id = ?
                """,
                    (hashed_backup_codes, user_id),
                )
                conn.commit()

                self.logger.info(f"Backup codes updated for user: {user_id}")
                return True
        except Exception as e:
            self.logger.error(f"Failed to update backup codes for user {user_id}: {e}")
            return False


# Глобальный экземпляр хранилища
_storage: Optional[UserStorage] = None


def get_storage(db_path: Optional[Path] = None) -> UserStorage:
    """Получить глобальный экземпляр хранилища"""
    global _storage
    if _storage is None:
        _storage = UserStorage(db_path)
    return _storage
