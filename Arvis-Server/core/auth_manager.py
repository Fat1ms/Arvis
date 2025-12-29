"""
Server-side authentication manager
Менеджер аутентификации на стороне сервера
"""

import hashlib
import hmac
import secrets
from datetime import datetime, timedelta
from typing import Optional, Tuple

from server.config import Settings
from server.core.jwt_handler import JWTHandler
from server.database.storage import DatabaseStorage


class ServerAuthManager:
    """Server-side authentication and user management"""

    def __init__(self, settings: Settings, storage: DatabaseStorage):
        self.settings = settings
        self.storage = storage
        self.jwt_handler = JWTHandler(settings)

        # Login attempt tracking
        self.login_attempts = {}  # username -> [timestamps]

    def hash_password(self, password: str, salt: str) -> str:
        """Hash password with salt using PBKDF2"""
        key = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 100_000)
        return key.hex()

    def verify_password(self, password: str, password_hash: str, salt: str) -> bool:
        """Verify password against hash"""
        expected_hash = self.hash_password(password, salt)
        return hmac.compare_digest(expected_hash, password_hash)

    def check_rate_limit(self, username: str) -> bool:
        """Check if login rate limit exceeded"""
        now = datetime.utcnow()
        window = now - timedelta(minutes=5)

        # Очистка старых попыток
        attempts = self.login_attempts.get(username, [])
        attempts = [ts for ts in attempts if ts > window]
        self.login_attempts[username] = attempts

        # Проверка лимита
        if len(attempts) >= self.settings.MAX_LOGIN_ATTEMPTS:
            return False

        return True

    def record_login_attempt(self, username: str):
        """Record login attempt"""
        if username not in self.login_attempts:
            self.login_attempts[username] = []
        self.login_attempts[username].append(datetime.utcnow())

    def authenticate(
        self, username: str, password: str, ip_address: Optional[str] = None
    ) -> Optional[Tuple[str, str, dict]]:
        """Authenticate user and return tokens + user info

        Returns:
            (access_token, refresh_token, user_dict) or None
        """
        # Rate limit check
        if not self.check_rate_limit(username):
            self.storage.log_audit(
                action="login",
                result="failure",
                username=username,
                ip_address=ip_address,
                details={"reason": "rate_limit_exceeded"},
            )
            return None

        # Record attempt
        self.record_login_attempt(username)

        # Get user
        user = self.storage.get_user_by_username(username)
        if not user:
            self.storage.log_audit(
                action="login",
                result="failure",
                username=username,
                ip_address=ip_address,
                details={"reason": "user_not_found"},
            )
            return None

        # Check active status
        if not user.is_active:
            self.storage.log_audit(
                action="login",
                result="failure",
                username=username,
                user_id=user.user_id,
                ip_address=ip_address,
                details={"reason": "account_inactive"},
            )
            return None

        # Verify password
        if not self.verify_password(password, user.password_hash, user.salt):
            self.storage.log_audit(
                action="login",
                result="failure",
                username=username,
                user_id=user.user_id,
                ip_address=ip_address,
                details={"reason": "invalid_password"},
            )
            return None

        # 2FA check (if enabled)
        if user.require_2fa:
            # Return special status indicating 2FA required
            return ("2fa_required", user.user_id, {"username": username, "user_id": user.user_id})

        # Generate tokens
        access_token, refresh_token = self.jwt_handler.create_token_pair(user.user_id, user.username, user.role)

        # Create session
        session_id = secrets.token_urlsafe(32)
        expires_at = datetime.utcnow() + timedelta(minutes=self.settings.SESSION_TIMEOUT_MINUTES)

        self.storage.create_session(
            session_id=session_id,
            user_id=user.user_id,
            expires_at=expires_at,
            ip_address=ip_address,
            access_token=access_token,
            refresh_token=refresh_token,
        )

        # Update last login
        self.storage.update_user(user.user_id, last_login=datetime.utcnow())

        # Audit log
        self.storage.log_audit(
            action="login",
            result="success",
            username=username,
            user_id=user.user_id,
            ip_address=ip_address,
        )

        # User info
        user_info = {
            "user_id": user.user_id,
            "username": user.username,
            "role": user.role,
            "require_2fa": user.require_2fa,
            "session_id": session_id,
        }

        return (access_token, refresh_token, user_info)

    def create_user(
        self, username: str, password: str, role: str = "user", admin_user_id: Optional[str] = None
    ) -> Optional[str]:
        """Create new user

        Returns:
            user_id or None
        """
        # Check if username exists
        existing = self.storage.get_user_by_username(username)
        if existing:
            return None

        # Generate user_id and salt
        user_id = secrets.token_urlsafe(16)
        salt = secrets.token_hex(32)

        # Hash password
        password_hash = self.hash_password(password, salt)

        # Create user
        user = self.storage.create_user(
            user_id=user_id,
            username=username,
            role=role,
            password_hash=password_hash,
            salt=salt,
        )

        # Audit log
        self.storage.log_audit(
            action="user_create",
            result="success",
            user_id=admin_user_id,
            resource=f"user:{user_id}",
            details={"username": username, "role": role},
        )

        return user.user_id if user else None

    def refresh_access_token(self, refresh_token: str) -> Optional[Tuple[str, str]]:
        """Refresh access token using refresh token

        Returns:
            (new_access_token, new_refresh_token) or None
        """
        # Verify refresh token
        payload = self.jwt_handler.verify_token(refresh_token, "refresh")
        if not payload:
            return None

        user_id = payload.get("sub")
        if not user_id:
            return None

        # Get user
        user = self.storage.get_user_by_id(user_id)
        if not user or not user.is_active:
            return None

        # Generate new token pair
        access_token, new_refresh_token = self.jwt_handler.create_token_pair(user.user_id, user.username, user.role)

        return (access_token, new_refresh_token)

    def logout(self, session_id: str, user_id: str):
        """Logout user and revoke session"""
        self.storage.revoke_session(session_id)
        self.storage.log_audit(
            action="logout",
            result="success",
            user_id=user_id,
        )

    def verify_access_token(self, token: str) -> Optional[dict]:
        """Verify access token and return user info"""
        user_info = self.jwt_handler.get_user_from_token(token)
        if not user_info:
            return None

        user_id, username, role = user_info
        return {
            "user_id": user_id,
            "username": username,
            "role": role,
        }
