"""
JWT token handler
Обработка JWT токенов для аутентификации
"""

import secrets
from datetime import datetime, timedelta
from typing import Optional, Tuple

from jose import JWTError, jwt

from server.config import Settings


class JWTHandler:
    """JWT token generation and validation"""

    def __init__(self, settings: Settings):
        self.secret_key = settings.JWT_SECRET_KEY
        self.algorithm = settings.JWT_ALGORITHM
        self.access_token_expire = settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES
        self.refresh_token_expire = settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS

    def create_access_token(
        self, user_id: str, username: str, role: str, expires_delta: Optional[timedelta] = None
    ) -> str:
        """Create JWT access token"""
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(minutes=self.access_token_expire)

        to_encode = {
            "sub": user_id,
            "username": username,
            "role": role,
            "type": "access",
            "exp": expire,
            "iat": datetime.utcnow(),
        }

        encoded_jwt = jwt.encode(to_encode, self.secret_key, algorithm=self.algorithm)
        return encoded_jwt

    def create_refresh_token(self, user_id: str, expires_delta: Optional[timedelta] = None) -> str:
        """Create JWT refresh token"""
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(days=self.refresh_token_expire)

        to_encode = {
            "sub": user_id,
            "type": "refresh",
            "exp": expire,
            "iat": datetime.utcnow(),
            "jti": secrets.token_urlsafe(32),  # Unique token ID
        }

        encoded_jwt = jwt.encode(to_encode, self.secret_key, algorithm=self.algorithm)
        return encoded_jwt

    def create_token_pair(self, user_id: str, username: str, role: str) -> Tuple[str, str]:
        """Create access and refresh token pair"""
        access_token = self.create_access_token(user_id, username, role)
        refresh_token = self.create_refresh_token(user_id)
        return access_token, refresh_token

    def verify_token(self, token: str, token_type: str = "access") -> Optional[dict]:
        """Verify and decode JWT token"""
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])

            # Проверяем тип токена
            if payload.get("type") != token_type:
                return None

            # Проверяем истечение
            exp = payload.get("exp")
            if exp and datetime.fromtimestamp(exp) < datetime.utcnow():
                return None

            return payload

        except JWTError:
            return None

    def decode_token(self, token: str) -> Optional[dict]:
        """Decode token without verification (для отладки)"""
        try:
            return jwt.decode(
                token,
                self.secret_key,
                algorithms=[self.algorithm],
                options={"verify_signature": False},
            )
        except JWTError:
            return None

    def get_user_from_token(self, token: str) -> Optional[Tuple[str, str, str]]:
        """Extract user info from access token"""
        payload = self.verify_token(token, "access")
        if not payload:
            return None

        user_id = payload.get("sub")
        username = payload.get("username")
        role = payload.get("role")

        if not all([user_id, username, role]):
            return None

        return user_id, username, role
