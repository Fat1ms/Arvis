"""
Settings migration between Launcher and Client
Handles transfer of global settings from client config to launcher
"""

from __future__ import annotations

import json
import shutil
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any, List

from PyQt6.QtCore import QObject, pyqtSignal


@dataclass
class MigrationResult:
    """Result of migration operation"""
    success: bool
    migrated_keys: List[str]
    errors: List[str]
    backup_path: Optional[Path] = None


class SettingsMigrator(QObject):
    """
    Handles settings migration between Launcher and Client.
    
    Settings categories:
    - GLOBAL (migrated to launcher): language, server_url, paths, startup options
    - LOCAL (stays in client): model behavior, TTS/STT settings, LLM parameters
    """
    
    # Signals
    migration_started = pyqtSignal()
    migration_progress = pyqtSignal(str)  # status message
    migration_complete = pyqtSignal(object)  # MigrationResult
    
    # Keys that belong to the launcher (global settings)
    LAUNCHER_KEYS = {
        "language.ui",           # UI language
        "api.server_url",        # Server URL for auth
        "api.api_key",           # API key
        "startup.autostart_ollama",
        "startup.autostart_server",
        "user.username",         # Current user
        "user.role",             # User role
        "logging.level",
        "logging.max_size_mb",
        "logging.backup_count",
    }
    
    # Keys that stay in client (behavior settings)
    CLIENT_KEYS = {
        "language.tts",          # TTS language
        "language.stt",          # STT language
        "tts",                   # All TTS settings
        "stt",                   # All STT settings
        "llm",                   # All LLM settings
        "modes",                 # Operation modes
        "security",              # Security settings
        "audit",                 # Audit settings
    }
    
    def __init__(self, launcher_config_path: Path, parent: Optional[QObject] = None):
        super().__init__(parent)
        self.launcher_config_path = Path(launcher_config_path)
    
    def detect_client_config(self, client_root: Path) -> Optional[Path]:
        """Find client config file"""
        config_path = client_root / "config" / "config.json"
        if config_path.exists():
            return config_path
        return None
    
    def needs_migration(self, client_root: Path) -> bool:
        """Check if migration is needed"""
        client_config = self.detect_client_config(client_root)
        if not client_config:
            return False
        
        try:
            client_data = json.loads(client_config.read_text(encoding="utf-8"))
            
            # Check if any launcher keys exist in client config
            for key in self.LAUNCHER_KEYS:
                parts = key.split(".")
                value = client_data
                for part in parts:
                    if isinstance(value, dict) and part in value:
                        value = value[part]
                    else:
                        value = None
                        break
                if value is not None:
                    return True
            
            return False
        except Exception:
            return False
    
    def migrate_from_client(self, client_root: Path) -> MigrationResult:
        """
        Migrate global settings from client to launcher.
        
        Steps:
        1. Backup client config
        2. Extract launcher-relevant settings
        3. Update launcher config
        4. Clean client config (remove migrated keys)
        """
        self.migration_started.emit()
        
        migrated_keys = []
        errors = []
        backup_path = None
        
        # Find client config
        client_config_path = self.detect_client_config(client_root)
        if not client_config_path:
            errors.append("Client config not found")
            return MigrationResult(False, migrated_keys, errors)
        
        try:
            # Read client config
            self.migration_progress.emit("Чтение конфигурации клиента...")
            client_data = json.loads(client_config_path.read_text(encoding="utf-8"))
            
            # Backup
            self.migration_progress.emit("Создание резервной копии...")
            backup_path = self._backup_config(client_config_path)
            
            # Read launcher config
            launcher_data = {}
            if self.launcher_config_path.exists():
                launcher_data = json.loads(
                    self.launcher_config_path.read_text(encoding="utf-8")
                )
            
            # Migrate settings
            self.migration_progress.emit("Миграция настроек...")
            
            # Language
            if "language" in client_data:
                lang = client_data["language"]
                if "ui" in lang:
                    launcher_data["language"] = lang["ui"]
                    migrated_keys.append("language.ui")
            
            # Server URL
            if "api" in client_data:
                api = client_data["api"]
                if "server_url" in api:
                    if "server" not in launcher_data:
                        launcher_data["server"] = {}
                    launcher_data["server"]["url"] = api["server_url"]
                    migrated_keys.append("api.server_url")
                if "api_key" in api:
                    if "server" not in launcher_data:
                        launcher_data["server"] = {}
                    launcher_data["server"]["api_key"] = api["api_key"]
                    migrated_keys.append("api.api_key")
            
            # Startup settings
            if "startup" in client_data:
                startup = client_data["startup"]
                if "autostart_ollama" in startup:
                    if "ollama" not in launcher_data:
                        launcher_data["ollama"] = {}
                    launcher_data["ollama"]["auto_start"] = startup["autostart_ollama"]
                    migrated_keys.append("startup.autostart_ollama")
            
            # User info
            if "user" in client_data:
                user = client_data["user"]
                if "username" in user and user["username"] != "Guest":
                    if "session" not in launcher_data:
                        launcher_data["session"] = {}
                    launcher_data["session"]["last_username"] = user["username"]
                    migrated_keys.append("user.username")
            
            # Logging
            if "logging" in client_data:
                logging = client_data["logging"]
                if "level" not in launcher_data:
                    launcher_data["logging"] = {}
                launcher_data["logging"] = logging.copy()
                migrated_keys.append("logging")
            
            # Save launcher config
            self.migration_progress.emit("Сохранение конфигурации лаунчера...")
            self.launcher_config_path.parent.mkdir(parents=True, exist_ok=True)
            self.launcher_config_path.write_text(
                json.dumps(launcher_data, ensure_ascii=False, indent=2),
                encoding="utf-8"
            )
            
            # Clean client config (remove migrated global keys)
            self.migration_progress.emit("Очистка конфигурации клиента...")
            cleaned_client = self._clean_client_config(client_data)
            client_config_path.write_text(
                json.dumps(cleaned_client, ensure_ascii=False, indent=2),
                encoding="utf-8"
            )
            
            self.migration_progress.emit("Миграция завершена!")
            result = MigrationResult(True, migrated_keys, errors, backup_path)
            self.migration_complete.emit(result)
            return result
            
        except Exception as e:
            errors.append(str(e))
            result = MigrationResult(False, migrated_keys, errors, backup_path)
            self.migration_complete.emit(result)
            return result
    
    def _backup_config(self, config_path: Path) -> Path:
        """Create backup of config file"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_dir = config_path.parent / "backups"
        backup_dir.mkdir(exist_ok=True)
        backup_path = backup_dir / f"config_{timestamp}.json"
        shutil.copy2(config_path, backup_path)
        return backup_path
    
    def _clean_client_config(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Remove launcher-specific keys from client config"""
        cleaned = config.copy()
        
        # Keep only client-relevant parts of language
        if "language" in cleaned:
            lang = cleaned["language"]
            # Keep tts and stt, remove ui (it's now in launcher)
            cleaned["language"] = {
                "tts": lang.get("tts", "ru"),
                "stt": lang.get("stt", "ru"),
            }
        
        # Clean api section - keep api_key for direct API calls
        if "api" in cleaned:
            api = cleaned["api"]
            cleaned["api"] = {
                "server_url": api.get("server_url", "http://127.0.0.1:8000"),
                "api_key": api.get("api_key"),
            }
        
        # Remove startup section (handled by launcher)
        if "startup" in cleaned:
            del cleaned["startup"]
        
        # Remove user section (handled by launcher session)
        if "user" in cleaned:
            # Keep minimal user info for offline mode
            cleaned["user"] = {
                "username": "Guest",
                "role": "guest",
            }
        
        return cleaned
    
    def sync_to_client(self, client_root: Path, launcher_config: Dict[str, Any]) -> bool:
        """
        Sync launcher settings back to client config.
        Called before launching client.
        """
        client_config_path = self.detect_client_config(client_root)
        if not client_config_path:
            return False
        
        try:
            client_data = json.loads(client_config_path.read_text(encoding="utf-8"))
            
            # Sync language
            if "language" in launcher_config:
                if "language" not in client_data:
                    client_data["language"] = {}
                client_data["language"]["ui"] = launcher_config["language"]
            
            # Sync server URL from session
            if "server" in launcher_config:
                if "api" not in client_data:
                    client_data["api"] = {}
                if "url" in launcher_config["server"]:
                    client_data["api"]["server_url"] = launcher_config["server"]["url"]
            
            # Save
            client_config_path.write_text(
                json.dumps(client_data, ensure_ascii=False, indent=2),
                encoding="utf-8"
            )
            return True
            
        except Exception:
            return False
    
    def restore_backup(self, backup_path: Path, client_root: Path) -> bool:
        """Restore config from backup"""
        client_config_path = self.detect_client_config(client_root)
        if not client_config_path or not backup_path.exists():
            return False
        
        try:
            shutil.copy2(backup_path, client_config_path)
            return True
        except Exception:
            return False
