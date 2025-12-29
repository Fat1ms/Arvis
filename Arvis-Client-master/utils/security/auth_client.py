"""
HTTP Authentication Client for Arvis
Клиент для работы с сервером аутентификации
"""

import json
from datetime import datetime
from typing import Optional, Tuple

import httpx

from utils.logger import ModuleLogger
from utils.security.rbac import Role


class AuthClient:
    """HTTP client for authentication server"""

    def __init__(self, server_url: str, timeout: float = 10.0):
        """
        Args:
            server_url: Base URL сервера (например, "http://192.168.1.100:8443")
            timeout: Timeout для запросов в секундах
        """
        self.server_url = server_url.rstrip("/")
        self.timeout = timeout
        self.logger = ModuleLogger("AuthClient")

        # Токены хранятся в памяти
        self.access_token: Optional[str] = None
        self.refresh_token: Optional[str] = None
        self.current_user: Optional[dict] = None

    def _make_request(
        self, method: str, endpoint: str, json_data: Optional[dict] = None, use_auth: bool = False
    ) -> Optional[dict]:
        """Make HTTP request to server"""
        url = f"{self.server_url}{endpoint}"
        headers = {}

        if use_auth and self.access_token:
            headers["Authorization"] = f"Bearer {self.access_token}"

        try:
            with httpx.Client(timeout=self.timeout) as client:
                if method == "GET":
                    response = client.get(url, headers=headers)
                elif method == "POST":
                    response = client.post(url, json=json_data, headers=headers)
                elif method == "PUT":
                    response = client.put(url, json=json_data, headers=headers)
                elif method == "DELETE":
                    response = client.delete(url, headers=headers)
                else:
                    self.logger.error(f"Unsupported HTTP method: {method}")
                    return None

                if response.status_code >= 400:
                    self.logger.error(f"HTTP {response.status_code}: {response.text}")
                    return None

                return response.json()

        except httpx.TimeoutException:
            self.logger.error(f"Request timeout to {url}")
            return None
        except Exception as e:
            self.logger.error(f"Request failed: {e}")
            return None

    def login(self, username: str, password: str) -> bool:
        """
        Login to server

        Returns:
            True if successful, False otherwise
        """
        self.logger.info(f"Attempting login for user: {username}")

        response = self._make_request(
            "POST",
            "/api/auth/login",
            json_data={"username": username, "password": password},
        )

        if not response:
            return False

        # Check if 2FA required
        if response.get("requires_2fa"):
            self.logger.info("2FA required for this account")
            # TODO: Implement 2FA flow
            return False

        # Save tokens
        self.access_token = response.get("access_token")
        self.refresh_token = response.get("refresh_token")
        self.current_user = response.get("user")

        self.logger.info(f"Login successful: {username}")
        return True

    def logout(self) -> bool:
        """Logout from server"""
        if not self.current_user:
            return True

        session_id = self.current_user.get("session_id")
        if not session_id:
            self.logger.warning("No session_id found, clearing local state")
            self._clear_session()
            return True

        response = self._make_request(
            "POST",
            "/api/auth/logout",
            json_data={"session_id": session_id},
            use_auth=True,
        )

        self._clear_session()
        return response is not None

    def _clear_session(self):
        """Clear session data"""
        self.access_token = None
        self.refresh_token = None
        self.current_user = None

    def refresh_tokens(self) -> bool:
        """Refresh access token"""
        if not self.refresh_token:
            return False

        response = self._make_request(
            "POST",
            "/api/auth/refresh",
            json_data={"refresh_token": self.refresh_token},
        )

        if not response:
            return False

        self.access_token = response.get("access_token")
        self.refresh_token = response.get("refresh_token")

        self.logger.info("Tokens refreshed successfully")
        return True

    def verify_token(self) -> bool:
        """Verify current access token"""
        if not self.access_token:
            return False

        response = self._make_request(
            "GET",
            f"/api/auth/verify?token={self.access_token}",
        )

        return response is not None

    def get_current_user(self) -> Optional[dict]:
        """Get current user info"""
        return self.current_user

    def is_authenticated(self) -> bool:
        """Check if user is authenticated"""
        return self.current_user is not None and self.access_token is not None

    # === User Management (Admin only) ===

    def list_users(self, include_inactive: bool = False) -> Optional[list]:
        """List all users"""
        response = self._make_request(
            "GET",
            f"/api/users?include_inactive={include_inactive}",
            use_auth=True,
        )

        if not response:
            return None

        return response.get("users", [])

    def create_user(self, username: str, password: str, role: str = "user") -> Optional[str]:
        """Create new user (returns user_id)"""
        response = self._make_request(
            "POST",
            "/api/users/",
            json_data={"username": username, "password": password, "role": role},
            use_auth=True,
        )

        if not response:
            return None

        return response.get("user_id")

    def update_user(
        self,
        user_id: str,
        role: Optional[str] = None,
        is_active: Optional[bool] = None,
        require_2fa: Optional[bool] = None,
    ) -> bool:
        """Update user"""
        update_data = {}
        if role is not None:
            update_data["role"] = role
        if is_active is not None:
            update_data["is_active"] = is_active
        if require_2fa is not None:
            update_data["require_2fa"] = require_2fa

        response = self._make_request(
            "PUT",
            f"/api/users/{user_id}",
            json_data=update_data,
            use_auth=True,
        )

        return response is not None

    def delete_user(self, user_id: str) -> bool:
        """Delete user"""
        response = self._make_request(
            "DELETE",
            f"/api/users/{user_id}",
            use_auth=True,
        )

        return response is not None

    def check_connection(self) -> bool:
        """Check if server is reachable"""
        try:
            response = self._make_request("GET", "/api/health")
            return response is not None and response.get("status") == "healthy"
        except Exception:
            return False
