"""
Session and authentication management for Arvis Launcher
Handles user login, token storage, and session persistence
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Dict, Any

import requests
from PyQt6.QtCore import QObject, pyqtSignal, QTimer


# Guest session limit in minutes
GUEST_SESSION_LIMIT_MINUTES = 30


@dataclass
class UserSession:
    """User session data"""
    username: str
    role: str = "guest"
    access_token: Optional[str] = None
    refresh_token: Optional[str] = None
    server_url: Optional[str] = None
    session_id: Optional[str] = None
    logged_in_at: Optional[str] = None
    is_guest: bool = False
    guest_expires_at: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "username": self.username,
            "role": self.role,
            "access_token": self.access_token,
            "refresh_token": self.refresh_token,
            "server_url": self.server_url,
            "session_id": self.session_id,
            "logged_in_at": self.logged_in_at,
            "is_guest": self.is_guest,
            "guest_expires_at": self.guest_expires_at,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "UserSession":
        return cls(
            username=data.get("username", "Guest"),
            role=data.get("role", "guest"),
            access_token=data.get("access_token"),
            refresh_token=data.get("refresh_token"),
            server_url=data.get("server_url"),
            session_id=data.get("session_id"),
            logged_in_at=data.get("logged_in_at"),
            is_guest=data.get("is_guest", False),
            guest_expires_at=data.get("guest_expires_at"),
        )
    
    @property
    def is_logged_in(self) -> bool:
        return self.access_token is not None and self.username != "Guest" and not self.is_guest
    
    @property
    def is_guest_session(self) -> bool:
        return self.is_guest
    
    @property
    def guest_time_remaining(self) -> Optional[int]:
        """Returns remaining guest time in seconds, or None if not a guest"""
        if not self.is_guest or not self.guest_expires_at:
            return None
        try:
            expires = datetime.fromisoformat(self.guest_expires_at)
            remaining = (expires - datetime.now()).total_seconds()
            return max(0, int(remaining))
        except Exception:
            return None


def get_session_dir() -> Path:
    """Get default session directory (same as launcher config)"""
    if os.name == "nt":
        base = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local"))
    else:
        base = Path.home() / ".config"
    return base / "ArvisLauncher"


class SessionManager(QObject):
    """Manages user sessions and authentication"""
    
    # Signals
    session_changed = pyqtSignal(object)  # UserSession or None
    login_success = pyqtSignal(str)       # username
    login_failed = pyqtSignal(str)        # error message
    logout_complete = pyqtSignal()
    guest_session_started = pyqtSignal(int)  # remaining seconds
    guest_session_tick = pyqtSignal(int)     # remaining seconds
    guest_session_expired = pyqtSignal()
    
    def __init__(self, parent: Optional[QObject] = None, config_dir: Optional[Path] = None):
        super().__init__(parent)
        self.config_dir = Path(config_dir) if config_dir else get_session_dir()
        self.session_file = self.config_dir / "session.json"
        self._session: Optional[UserSession] = None
        
        # Guest session timer
        self._guest_timer = QTimer(self)
        self._guest_timer.timeout.connect(self._on_guest_timer_tick)
        
        self._load_session()
        
        # Check if loaded session is an expired guest
        if self._session and self._session.is_guest:
            remaining = self._session.guest_time_remaining
            if remaining is not None and remaining <= 0:
                self._session = None
                self._save_session()
            elif remaining is not None:
                self._start_guest_timer()
    
    @property
    def session(self) -> Optional[UserSession]:
        return self._session
    
    @property
    def is_logged_in(self) -> bool:
        return self._session is not None and self._session.is_logged_in
    
    @property
    def is_guest(self) -> bool:
        return self._session is not None and self._session.is_guest
    
    def to_dict(self) -> Dict[str, Any]:
        """Return session as dictionary for passing to client"""
        if self._session:
            return self._session.to_dict()
        return {}
    
    def _load_session(self) -> None:
        """Load session from file"""
        if self.session_file.exists():
            try:
                data = json.loads(self.session_file.read_text(encoding="utf-8"))
                self._session = UserSession.from_dict(data)
            except Exception:
                self._session = None
    
    def _save_session(self) -> None:
        """Save session to file"""
        self.config_dir.mkdir(parents=True, exist_ok=True)
        if self._session:
            data = self._session.to_dict()
            self.session_file.write_text(
                json.dumps(data, ensure_ascii=False, indent=2),
                encoding="utf-8"
            )
        elif self.session_file.exists():
            self.session_file.unlink()
    
    def start_guest_session(self) -> None:
        """
        Start a guest session with 30-minute time limit.
        Guest sessions have limited functionality and expire automatically.
        """
        expires_at = datetime.now() + timedelta(minutes=GUEST_SESSION_LIMIT_MINUTES)
        
        self._session = UserSession(
            username="Гость",
            role="guest",
            access_token=None,
            refresh_token=None,
            server_url=None,
            session_id=None,
            logged_in_at=datetime.now().isoformat(),
            is_guest=True,
            guest_expires_at=expires_at.isoformat(),
        )
        self._save_session()
        self._start_guest_timer()
        self.session_changed.emit(self._session)
        self.guest_session_started.emit(GUEST_SESSION_LIMIT_MINUTES * 60)
    
    def _start_guest_timer(self) -> None:
        """Start the guest session countdown timer"""
        self._guest_timer.start(1000)  # Tick every second
    
    def _stop_guest_timer(self) -> None:
        """Stop the guest session timer"""
        self._guest_timer.stop()
    
    def _on_guest_timer_tick(self) -> None:
        """Handle guest timer tick"""
        if not self._session or not self._session.is_guest:
            self._stop_guest_timer()
            return
        
        remaining = self._session.guest_time_remaining
        if remaining is None or remaining <= 0:
            self._stop_guest_timer()
            self._session = None
            self._save_session()
            self.guest_session_expired.emit()
            self.session_changed.emit(None)
        else:
            self.guest_session_tick.emit(remaining)
    
    def get_guest_time_remaining(self) -> Optional[int]:
        """Get remaining guest session time in seconds"""
        if self._session and self._session.is_guest:
            return self._session.guest_time_remaining
        return None
    
    def login(self, server_url: str, username: str, password: str) -> bool:
        """
        Login to server
        
        Args:
            server_url: Server base URL (e.g., "http://127.0.0.1:8000")
            username: Username
            password: Password
            
        Returns:
            True if login successful
        """
        server_url = server_url.rstrip("/")
        
        try:
            response = requests.post(
                f"{server_url}/api/auth/login",
                json={"username": username, "password": password},
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                
                # Check if 2FA required
                if data.get("requires_2fa"):
                    self.login_failed.emit("Требуется двухфакторная аутентификация")
                    return False
                
                # Save session
                user_data = data.get("user", {})
                self._session = UserSession(
                    username=user_data.get("username", username),
                    role=user_data.get("role", "user"),
                    access_token=data.get("access_token"),
                    refresh_token=data.get("refresh_token"),
                    server_url=server_url,
                    session_id=user_data.get("session_id"),
                    logged_in_at=datetime.now().isoformat(),
                )
                self._save_session()
                self.session_changed.emit(self._session)
                self.login_success.emit(username)
                return True
            else:
                error = response.json().get("detail", "Ошибка авторизации")
                self.login_failed.emit(error)
                return False
                
        except requests.exceptions.ConnectionError:
            self.login_failed.emit("Сервер недоступен")
            return False
        except requests.exceptions.Timeout:
            self.login_failed.emit("Превышено время ожидания")
            return False
        except Exception as e:
            self.login_failed.emit(str(e))
            return False
    
    def logout(self) -> None:
        """Logout and clear session"""
        if self._session and self._session.server_url and self._session.access_token:
            try:
                requests.post(
                    f"{self._session.server_url}/api/auth/logout",
                    json={"session_id": self._session.session_id},
                    headers={"Authorization": f"Bearer {self._session.access_token}"},
                    timeout=5
                )
            except Exception:
                pass  # Ignore errors during logout
        
        self._stop_guest_timer()
        self._session = None
        self._save_session()
        self.session_changed.emit(None)
        self.logout_complete.emit()
    
    def refresh_tokens(self) -> bool:
        """Refresh access token"""
        if not self._session or not self._session.refresh_token:
            return False
        
        try:
            response = requests.post(
                f"{self._session.server_url}/api/auth/refresh",
                json={"refresh_token": self._session.refresh_token},
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                self._session.access_token = data.get("access_token")
                self._session.refresh_token = data.get("refresh_token")
                self._save_session()
                return True
                
        except Exception:
            pass
        
        return False
    
    def verify_session(self) -> bool:
        """Verify current session is still valid"""
        if not self._session or not self._session.access_token:
            return False
        
        try:
            response = requests.get(
                f"{self._session.server_url}/api/auth/verify",
                params={"token": self._session.access_token},
                timeout=5
            )
            return response.status_code == 200
        except Exception:
            return False
    
    def get_auth_headers(self) -> Dict[str, str]:
        """Get authorization headers for API requests"""
        if self._session and self._session.access_token:
            return {"Authorization": f"Bearer {self._session.access_token}"}
        return {}
    
    def migrate_from_client(self, client_config_path: Path) -> bool:
        """
        Migrate session from client config.json to launcher
        
        Args:
            client_config_path: Path to client's config.json
            
        Returns:
            True if session was migrated
        """
        if not client_config_path.exists():
            return False
        
        try:
            data = json.loads(client_config_path.read_text(encoding="utf-8"))
            
            # Check for user/auth data in client config
            api_config = data.get("api", {})
            user_config = data.get("user", {})
            
            # Look for tokens
            access_token = api_config.get("access_token") or user_config.get("access_token")
            refresh_token = api_config.get("refresh_token") or user_config.get("refresh_token")
            server_url = api_config.get("server_url", "http://127.0.0.1:8000")
            username = user_config.get("username") or user_config.get("login") or "User"
            role = user_config.get("role", "user")
            
            if access_token:
                self._session = UserSession(
                    username=username,
                    role=role,
                    access_token=access_token,
                    refresh_token=refresh_token,
                    server_url=server_url.rstrip("/"),
                    logged_in_at=datetime.now().isoformat(),
                )
                self._save_session()
                self.session_changed.emit(self._session)
                return True
        except Exception:
            pass
        
        return False
