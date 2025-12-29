"""
Configuration management for Arvis Launcher
"""

from __future__ import annotations

import json
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


@dataclass
class WindowConfig:
    """Window size and position configuration"""
    width: int = 1000
    height: int = 650
    x: Optional[int] = None
    y: Optional[int] = None


@dataclass
class PathsConfig:
    """Path configurations"""
    client_root: Optional[str] = None
    models_dir: Optional[str] = None
    logs_dir: Optional[str] = None


@dataclass
class UpdateConfig:
    """Update settings"""
    auto_check: bool = True
    branch: str = "stable"  # stable / dev
    github_repo: str = "Fat1ms/Arvis-Client"


@dataclass
class OllamaConfig:
    """Ollama settings"""
    auto_install: bool = True
    default_model: str = "gemma2:2b"
    auto_start: bool = False


@dataclass
class UserConfig:
    """User profile settings"""
    name: str = ""
    city: str = ""


@dataclass
class LanguageConfig:
    """Language settings"""
    ui: str = "ru"  # UI language
    speech: str = "ru"  # STT/TTS language


@dataclass
class VoiceModelsConfig:
    """Voice models settings"""
    stt_model: str = ""  # Selected STT model (vosk model folder name)
    tts_model: str = "v3_1_ru"  # Selected TTS model (silero model name)
    tts_voice: str = "aidar"  # Selected TTS voice


@dataclass
class LauncherConfig:
    """Main launcher configuration"""
    
    window: WindowConfig = field(default_factory=WindowConfig)
    paths: PathsConfig = field(default_factory=PathsConfig)
    update: UpdateConfig = field(default_factory=UpdateConfig)
    ollama: OllamaConfig = field(default_factory=OllamaConfig)
    user: UserConfig = field(default_factory=UserConfig)
    languages: LanguageConfig = field(default_factory=LanguageConfig)
    voice_models: VoiceModelsConfig = field(default_factory=VoiceModelsConfig)
    
    # UI preferences
    autoscroll_logs: bool = True
    language: str = "ru"  # DEPRECATED: use languages.ui instead
    
    # Installation state
    first_run: bool = True
    installed_version: Optional[str] = None
    migration_done: bool = False
    
    _config_path: Optional[Path] = field(default=None, repr=False)
    
    @staticmethod
    def _get_launcher_dir() -> Path:
        """Get the directory where launcher executable/script is located"""
        # PyInstaller frozen executable
        if getattr(sys, 'frozen', False):
            return Path(sys.executable).resolve().parent
        # Running as script - use argv[0]
        try:
            argv0 = Path(sys.argv[0]).resolve()
            if argv0.suffix.lower() == ".py":
                return argv0.parent
        except Exception:
            pass
        return Path.cwd()
    
    @staticmethod
    def _get_config_path() -> Path:
        """Get default config file path"""
        return LauncherConfig._get_launcher_dir() / "launcher_config.json"
    
    @classmethod
    def _detect_client_root(cls) -> Optional[Path]:
        """Try to auto-detect Arvis Client location"""
        launcher_dir = cls._get_launcher_dir()
        
        # Check various possible locations
        candidates = [
            launcher_dir / "Arvis-Client",           # Subfolder
            launcher_dir / "client",                  # Subfolder
            launcher_dir.parent / "Arvis-Client",    # Sibling folder
            launcher_dir.parent / "Arvis-Client-master",
            launcher_dir,                             # Same folder as launcher
        ]
        
        for candidate in candidates:
            if (candidate / "launch.py").exists() or (candidate / "main.py").exists():
                return candidate
        
        return None
    
    @classmethod
    def load(cls, path: Optional[Path] = None) -> "LauncherConfig":
        """Load configuration from file, creating default if not exists"""
        if path is None:
            path = cls._get_config_path()
        
        config = cls()
        config._config_path = path
        
        # Auto-detect client root if not set
        detected_root = cls._detect_client_root()
        if detected_root:
            config.paths.client_root = str(detected_root)
        
        if not path.exists():
            config.save()
            return config
        
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            config._load_from_dict(data)
        except Exception:
            # Corrupted config - save defaults
            config.save()
        
        return config
    
    def _load_from_dict(self, data: dict) -> None:
        """Load configuration from dictionary"""
        # Window config
        if "window" in data and isinstance(data["window"], dict):
            w = data["window"]
            self.window.width = int(w.get("width", self.window.width))
            self.window.height = int(w.get("height", self.window.height))
            self.window.x = w.get("x")
            self.window.y = w.get("y")
        
        # Paths config
        if "paths" in data and isinstance(data["paths"], dict):
            p = data["paths"]
            self.paths.client_root = p.get("client_root", self.paths.client_root)
            self.paths.models_dir = p.get("models_dir")
            self.paths.logs_dir = p.get("logs_dir")
        
        # Update config
        if "update" in data and isinstance(data["update"], dict):
            u = data["update"]
            self.update.auto_check = bool(u.get("auto_check", self.update.auto_check))
            self.update.branch = str(u.get("branch", self.update.branch))
            self.update.github_repo = str(u.get("github_repo", self.update.github_repo))
        
        # Ollama config
        if "ollama" in data and isinstance(data["ollama"], dict):
            o = data["ollama"]
            self.ollama.auto_install = bool(o.get("auto_install", self.ollama.auto_install))
            self.ollama.default_model = str(o.get("default_model", self.ollama.default_model))
            self.ollama.auto_start = bool(o.get("auto_start", self.ollama.auto_start))
        
        # User config
        if "user" in data and isinstance(data["user"], dict):
            u = data["user"]
            self.user.name = str(u.get("name", self.user.name))
            self.user.city = str(u.get("city", self.user.city))
        
        # Languages config
        if "languages" in data and isinstance(data["languages"], dict):
            l = data["languages"]
            self.languages.ui = str(l.get("ui", self.languages.ui))
            self.languages.speech = str(l.get("speech", self.languages.speech))
        
        # Voice models config
        if "voice_models" in data and isinstance(data["voice_models"], dict):
            v = data["voice_models"]
            self.voice_models.stt_model = str(v.get("stt_model", self.voice_models.stt_model))
            self.voice_models.tts_model = str(v.get("tts_model", self.voice_models.tts_model))
            self.voice_models.tts_voice = str(v.get("tts_voice", self.voice_models.tts_voice))
        
        # Other settings
        self.autoscroll_logs = bool(data.get("autoscroll_logs", self.autoscroll_logs))
        # Migrate old language field to languages.ui
        old_lang = data.get("language")
        if old_lang and "languages" not in data:
            self.languages.ui = str(old_lang)
        self.language = self.languages.ui  # Keep in sync for backward compat
        self.first_run = bool(data.get("first_run", self.first_run))
        self.installed_version = data.get("installed_version")
        self.migration_done = bool(data.get("migration_done", self.migration_done))
    
    def get_config_path(self) -> Path:
        """Get the path to the config file"""
        return self._config_path or self._get_config_path()
    
    def save(self) -> None:
        """Save configuration to file"""
        path = self._config_path or self._get_config_path()
        self._config_path = path
        
        data = {
            "window": {
                "width": self.window.width,
                "height": self.window.height,
                "x": self.window.x,
                "y": self.window.y,
            },
            "paths": {
                "client_root": self.paths.client_root,
                "models_dir": self.paths.models_dir,
                "logs_dir": self.paths.logs_dir,
            },
            "update": {
                "auto_check": self.update.auto_check,
                "branch": self.update.branch,
                "github_repo": self.update.github_repo,
            },
            "ollama": {
                "auto_install": self.ollama.auto_install,
                "default_model": self.ollama.default_model,
                "auto_start": self.ollama.auto_start,
            },
            "user": {
                "name": self.user.name,
                "city": self.user.city,
            },
            "languages": {
                "ui": self.languages.ui,
                "speech": self.languages.speech,
            },
            "voice_models": {
                "stt_model": self.voice_models.stt_model,
                "tts_model": self.voice_models.tts_model,
                "tts_voice": self.voice_models.tts_voice,
            },
            "autoscroll_logs": self.autoscroll_logs,
            "language": self.languages.ui,  # Backward compat
            "first_run": self.first_run,
            "installed_version": self.installed_version,
            "migration_done": self.migration_done,
        }
        
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    
    def get_client_root(self) -> Optional[Path]:
        """Get client root as Path, if configured"""
        if self.paths.client_root:
            return Path(self.paths.client_root)
        return None
    
    def get_models_dir(self) -> Path:
        """Get models directory, with fallback to default"""
        if self.paths.models_dir:
            return Path(self.paths.models_dir)
        client = self.get_client_root()
        if client:
            return client / "models"
        return self._get_launcher_dir() / "models"
    
    def get_logs_dir(self) -> Path:
        """Get logs directory"""
        if self.paths.logs_dir:
            return Path(self.paths.logs_dir)
        return self._get_launcher_dir() / "logs"
