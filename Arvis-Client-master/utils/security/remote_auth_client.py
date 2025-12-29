"""
Remote Authentication Client for Arvis
Клиент удаленной аутентификации для Arvis
"""

import json
from datetime import datetime
from typing import Dict, Optional, Tuple

import requests

from utils.logger import ModuleLogger
from config.config import Config


class RemoteAuthClient:
    """Client for remote authentication server"""

    _instance: Optional["RemoteAuthClient"] = None

    def __init__(self, server_url: str, timeout: int = 10):
        """
        Initialize remote auth client

        Args:
            server_url: Base URL of authentication server (e.g., "http://192.168.1.100:8000")
            timeout: Request timeout in seconds
        """
        self.logger = ModuleLogger("RemoteAuthClient")
        self.server_url = server_url.rstrip("/")
        self.timeout = timeout
        self.access_token: Optional[str] = None
        self.session_id: Optional[str] = None
        self.current_user: Optional[Dict] = None

        self.logger.info(f"Remote auth client initialized: {self.server_url}")

    def _make_request(
        self, method: str, endpoint: str, data: Optional[Dict] = None, auth: bool = False
    ) -> Tuple[bool, Optional[Dict]]:
        """
        Make HTTP request to server

        Args:
            method: HTTP method (GET, POST, etc.)
            endpoint: API endpoint
            data: Request data
            auth: Include authorization header

        Returns:
            Tuple of (success, response_data)
        """
        url = f"{self.server_url}{endpoint}"
        headers = {"Content-Type": "application/json"}

        if auth and self.access_token:
            headers["Authorization"] = f"Bearer {self.access_token}"

        try:
            if method == "GET":
                response = requests.get(url, headers=headers, timeout=self.timeout)
            elif method == "POST":
                response = requests.post(url, headers=headers, json=data, timeout=self.timeout)
            elif method == "PUT":
                response = requests.put(url, headers=headers, json=data, timeout=self.timeout)
            elif method == "DELETE":
                response = requests.delete(url, headers=headers, timeout=self.timeout)
            else:
                self.logger.error(f"Unsupported HTTP method: {method}")
                return False, None

            if response.status_code < 300:
                try:
                    return True, response.json()
                except Exception:
                    return True, {}
            else:
                error_detail = response.json().get("detail", "Unknown error")
                self.logger.error(f"Server error ({response.status_code}): {error_detail}")
                return False, {"error": error_detail}

        except requests.exceptions.ConnectionError:
            self.logger.error(f"Connection error: Cannot connect to {url}")
            return False, {"error": "Cannot connect to authentication server"}
        except requests.exceptions.Timeout:
            self.logger.error(f"Timeout error: Request to {url} timed out")
            return False, {"error": "Authentication server timeout"}
        except Exception as e:
            self.logger.error(f"Request error: {e}")
            return False, {"error": str(e)}

    def login(self, username: str, password: str, device_name: Optional[str] = None) -> Tuple[bool, Dict]:
        """
        Login to remote server

        Args:
            username: Username
            password: Password
            device_name: Optional device identifier

        Returns:
            Tuple of (success, user_data)
            user_data contains: user_id, username, role, access_token, session_id, require_2fa
        """
        data = {"username": username, "password": password}

        if device_name:
            data["device_name"] = device_name

        success, response = self._make_request("POST", "/api/auth/login", data)

        if success and response:
            # Check if 2FA is required
            if response.get("require_2fa"):
                self.logger.info("2FA required for user")
                return True, {
                    "user_id": response.get("user_id"),
                    "username": response.get("username"),
                    "role": response.get("role"),
                    "require_2fa": True,
                    "access_token": None,
                    "session_id": None,
                }

            # Store tokens
            self.access_token = response.get("access_token")
            self.session_id = response.get("session_id")

            user_data = {
                "user_id": response.get("user_id"),
                "username": response.get("username"),
                "role": response.get("role"),
                "require_2fa": False,
                "access_token": self.access_token,
                "session_id": self.session_id,
            }

            self.current_user = user_data

            self.logger.info(f"Login successful: {username} (role: {user_data['role']})")
            return True, user_data

        error_msg = response.get("error", "Unknown error") if response else "No response"
        self.logger.error(f"Login failed: {error_msg}")
        return False, {"error": error_msg}

    def login_with_totp(self, username: str, password: str, totp_code: str, device_name: Optional[str] = None) -> Tuple[bool, Dict]:
        """
        Second-step login when server requires 2FA. Reuses /api/auth/login with totp_code.
        """
        data = {"username": username, "password": password, "totp_code": totp_code}
        if device_name:
            data["device_name"] = device_name

        success, response = self._make_request("POST", "/api/auth/login", data)
        if success and response and response.get("access_token"):
            self.access_token = response.get("access_token")
            self.session_id = response.get("session_id")
            self.current_user = {
                "user_id": response.get("user_id"),
                "username": response.get("username"),
                "role": response.get("role"),
                "access_token": self.access_token,
                "session_id": self.session_id,
            }
            return True, self.current_user
        return False, {"error": (response or {}).get("error", "2FA verification failed")}

    def guest_login(self) -> Tuple[bool, Dict]:
        """
        Login as guest

        Returns:
            Tuple of (success, user_data)
        """
        success, response = self._make_request("POST", "/api/auth/guest")

        if success and response:
            self.access_token = response.get("access_token")
            self.session_id = response.get("session_id")

            user_data = {
                "user_id": response.get("user_id"),
                "username": response.get("username"),
                "role": response.get("role"),
                "access_token": self.access_token,
                "session_id": self.session_id,
            }

            self.logger.info("Guest login successful")
            return True, user_data

        error_msg = response.get("error", "Unknown error") if response else "No response"
        self.logger.error(f"Guest login failed: {error_msg}")
        return False, {"error": error_msg}

    def logout(self) -> bool:
        """
        Logout from server

        Returns:
            Success status
        """
        if not self.access_token:
            return True

        success, _ = self._make_request("POST", "/api/auth/logout", auth=True)

        if success:
            self.access_token = None
            self.session_id = None
            self.current_user = None
            self.logger.info("Logout successful")
            return True

        self.logger.error("Logout failed")
        return False

    def get_user_info(self) -> Optional[Dict]:
        """
        Get current user information

        Returns:
            User info dictionary or None
        """
        if not self.access_token:
            self.logger.error("Not authenticated")
            return None

        success, response = self._make_request("GET", "/api/auth/me", auth=True)

        if success and response:
            return response

        return None

    def check_permission(self, permission: str) -> bool:
        """
        Check if current user has permission

        Args:
            permission: Permission to check (e.g., "module.weather")

        Returns:
            True if user has permission
        """
        if not self.access_token:
            self.logger.error("Not authenticated")
            return False

        data = {"permission": permission}
        success, response = self._make_request("POST", "/api/auth/check-permission", data, auth=True)

        if success and response:
            return response.get("allowed", False)

        return False

    def health_check(self) -> bool:
        """
        Check if server is healthy

        Returns:
            True if server is accessible
        """
        success, _ = self._make_request("GET", "/api/auth/health")
        return success

    def is_authenticated(self) -> bool:
        """Check if client has valid authentication"""
        return self.access_token is not None

    @classmethod
    def get(cls) -> "RemoteAuthClient":
        """Singleton accessor configured via app Config"""
        if cls._instance is None:
            cfg = Config()
            server_url = cfg.get_auth_server_url()
            cls._instance = RemoteAuthClient(server_url=server_url, timeout=10)
        return cls._instance

    def create_user(self, username: str, password: str, email: Optional[str] = None, role: str = "user") -> Tuple[bool, Optional[Dict]]:
        """
        Create a new user on remote server (requires admin authentication)

        Args:
            username: Username for new user
            password: Password for new user
            email: Optional email address
            role: User role (guest, user, power_user, admin)

        Returns:
            Tuple of (success, user_data or error)
        """
        if not self.access_token:
            self.logger.error("Not authenticated - cannot create user")
            return False, {"error": "Authentication required"}

        data = {
            "username": username,
            "password": password,
            "role": role
        }

        if email:
            data["email"] = email

        success, response = self._make_request("POST", "/api/users/", data, auth=True)

        if success and response:
            self.logger.info(f"User created successfully: {username} (role: {role})")
            return True, response

        error_msg = response.get("error", "Unknown error") if response else "No response"
        self.logger.error(f"Failed to create user: {error_msg}")
        return False, {"error": error_msg}

    def list_users(self, skip: int = 0, limit: int = 100) -> Tuple[bool, Optional[list]]:
        """
        Get list of all users from server (requires admin authentication)

        Args:
            skip: Number of users to skip
            limit: Maximum number of users to return

        Returns:
            Tuple of (success, user_list or error)
        """
        if not self.access_token:
            self.logger.error("Not authenticated - cannot list users")
            return False, None

        endpoint = f"/api/users/?skip={skip}&limit={limit}"
        success, response = self._make_request("GET", endpoint, auth=True)

        if success and response:
            self.logger.debug(f"Retrieved {len(response)} users from server")
            return True, response

        error_msg = response.get("error", "Unknown error") if response else "No response"
        self.logger.error(f"Failed to list users: {error_msg}")
        return False, None

    def get_user(self, user_id: str) -> Tuple[bool, Optional[Dict]]:
        """
        Get user information by ID (requires admin authentication)

        Args:
            user_id: User ID to retrieve

        Returns:
            Tuple of (success, user_data or None)
        """
        if not self.access_token:
            self.logger.error("Not authenticated - cannot get user")
            return False, None

        success, response = self._make_request("GET", f"/api/users/{user_id}", auth=True)

        if success and response:
            return True, response

        error_msg = response.get("error", "Unknown error") if response else "No response"
        self.logger.error(f"Failed to get user: {error_msg}")
        return False, None

    def update_user(self, user_id: str, email: Optional[str] = None, role: Optional[str] = None, is_active: Optional[bool] = None) -> Tuple[bool, Optional[Dict]]:
        """
        Update user information (requires admin authentication)

        Args:
            user_id: User ID to update
            email: New email (optional)
            role: New role (optional)
            is_active: Active status (optional)

        Returns:
            Tuple of (success, updated_user_data or error)
        """
        if not self.access_token:
            self.logger.error("Not authenticated - cannot update user")
            return False, {"error": "Authentication required"}

        data = {}
        if email is not None:
            data["email"] = email
        if role is not None:
            data["role"] = role
        if is_active is not None:
            data["is_active"] = is_active

        success, response = self._make_request("PUT", f"/api/users/{user_id}", data, auth=True)

        if success and response:
            self.logger.info(f"User updated successfully: {user_id}")
            return True, response

        error_msg = response.get("error", "Unknown error") if response else "No response"
        self.logger.error(f"Failed to update user: {error_msg}")
        return False, {"error": error_msg}

    def delete_user(self, user_id: str) -> bool:
        """
        Delete user (requires admin authentication)

        Args:
            user_id: User ID to delete

        Returns:
            Success status
        """
        if not self.access_token:
            self.logger.error("Not authenticated - cannot delete user")
            return False

        success, response = self._make_request("DELETE", f"/api/users/{user_id}", auth=True)

        if success:
            self.logger.info(f"User deleted successfully: {user_id}")
            return True

        error_msg = response.get("error", "Unknown error") if response else "No response"
        self.logger.error(f"Failed to delete user: {error_msg}")
        return False
