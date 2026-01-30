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
    auto_hide_on_client_start: bool = True  # Hide launcher when client starts
    minimize_to_tray: bool = False  # Minimize to system tray instead of taskbar


@dataclass
class StartupConfig:
    """Startup settings"""
    run_on_system_start: bool = False  # Autostart launcher with Windows
    auto_start_client: bool = False  # Automatically start Arvis Client when launcher opens


@dataclass
class PathsConfig:
    """Path configurations"""
    client_root: Optional[str] = None
    models_dir: Optional[str] = None
    logs_dir: Optional[str] = None
    client_logs_dir: Optional[str] = None


@dataclass
class UpdateConfig:
    """Update settings"""
    auto_check: bool = True
    branch: str = "stable"  # stable / dev
    github_repo: str = "Fat1ms/Arvis"


@dataclass
class OllamaConfig:
    """Ollama settings"""
    auto_install: bool = True
    default_model: str = "gemma2:2b"
    auto_start: bool = False
    temperature: float = 0.7


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
    tts_engine: str = "silero"  # Selected TTS engine (silero, piper, kokoro, styletts2, f5tts, bark)
    tts_model: str = "v3_1_ru"  # Selected TTS model (engine-specific)
    tts_voice: str = "aidar"  # Selected TTS voice


@dataclass
class ActivationConfig:
    """Activation settings"""
    enabled: bool = True  # Whether activation is required
    server_url: str = "http://localhost:8080"  # Activation server URL
    check_interval_hours: int = 24  # How often to check online
    offline_grace_days: int = 7  # Days allowed without online validation


@dataclass
class ApiKeysConfig:
    """API keys for external services"""
    server_api_key: str = ""  # Server API key
    weather_api_key: str = ""  # Weather API key (OpenWeatherMap)
    news_api_key: str = ""  # News API key
    search_api_key: str = ""  # Search API key (Google CSE)
    search_engine_id: str = ""  # Google Search Engine ID


@dataclass
class LoggingConfig:
    """Logging settings"""
    level: str = "INFO"  # DEBUG, INFO, WARNING, ERROR
    max_size_mb: int = 10
    backup_count: int = 5
    file_logging: bool = True


@dataclass
class OllamaServerConfig:
    """Ollama server settings"""
    url: str = "http://127.0.0.1:11434"
    launch_mode: str = "console"  # console, background, service
    bind_address: str = "127.0.0.1"
    allow_external: bool = False
    auto_restart: bool = True


@dataclass
class LauncherConfig:
    """Main launcher configuration"""
    
    window: WindowConfig = field(default_factory=WindowConfig)
    paths: PathsConfig = field(default_factory=PathsConfig)
    update: UpdateConfig = field(default_factory=UpdateConfig)
    ollama: OllamaConfig = field(default_factory=OllamaConfig)
    ollama_server: OllamaServerConfig = field(default_factory=OllamaServerConfig)
    user: UserConfig = field(default_factory=UserConfig)
    languages: LanguageConfig = field(default_factory=LanguageConfig)
    voice_models: VoiceModelsConfig = field(default_factory=VoiceModelsConfig)
    activation: ActivationConfig = field(default_factory=ActivationConfig)
    startup: StartupConfig = field(default_factory=StartupConfig)
    api_keys: ApiKeysConfig = field(default_factory=ApiKeysConfig)
    logging: LoggingConfig = field(default_factory=LoggingConfig)
    # Preserve detailed subsystem configs migrated from client
    tts: dict = field(default_factory=dict)
    stt: dict = field(default_factory=dict)
    llm: dict = field(default_factory=dict)
    modules: dict = field(default_factory=dict)
    
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
            self.window.auto_hide_on_client_start = bool(w.get("auto_hide_on_client_start", self.window.auto_hide_on_client_start))
            self.window.minimize_to_tray = bool(w.get("minimize_to_tray", self.window.minimize_to_tray))
        
        # Paths config
        if "paths" in data and isinstance(data["paths"], dict):
            p = data["paths"]
            self.paths.client_root = p.get("client_root", self.paths.client_root)
            self.paths.models_dir = p.get("models_dir")
            self.paths.logs_dir = p.get("logs_dir")
            self.paths.client_logs_dir = p.get("client_logs_dir")
        
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
            # LLM temperature for Ollama provider
            try:
                self.ollama.temperature = float(o.get("temperature", self.ollama.temperature))
            except Exception:
                pass
        
        # Ollama server config
        if "ollama_server" in data and isinstance(data["ollama_server"], dict):
            o = data["ollama_server"]
            self.ollama_server.url = str(o.get("url", self.ollama_server.url))
            self.ollama_server.launch_mode = str(o.get("launch_mode", self.ollama_server.launch_mode))
            self.ollama_server.bind_address = str(o.get("bind_address", self.ollama_server.bind_address))
            self.ollama_server.allow_external = bool(o.get("allow_external", self.ollama_server.allow_external))
            self.ollama_server.auto_restart = bool(o.get("auto_restart", self.ollama_server.auto_restart))
        
        # API keys config
        if "api_keys" in data and isinstance(data["api_keys"], dict):
            a = data["api_keys"]
            self.api_keys.server_api_key = str(a.get("server_api_key", self.api_keys.server_api_key))
            self.api_keys.weather_api_key = str(a.get("weather_api_key", self.api_keys.weather_api_key))
            self.api_keys.news_api_key = str(a.get("news_api_key", self.api_keys.news_api_key))
            self.api_keys.search_api_key = str(a.get("search_api_key", self.api_keys.search_api_key))
            self.api_keys.search_engine_id = str(a.get("search_engine_id", self.api_keys.search_engine_id))
        
        # Logging config
        if "logging" in data and isinstance(data["logging"], dict):
            l = data["logging"]
            self.logging.level = str(l.get("level", self.logging.level))
            self.logging.max_size_mb = int(l.get("max_size_mb", self.logging.max_size_mb))
            self.logging.backup_count = int(l.get("backup_count", self.logging.backup_count))
            self.logging.file_logging = bool(l.get("file_logging", self.logging.file_logging))
        
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

        # Preserve raw subsystem configs if present (tts/stt/llm/modules)
        if "tts" in data and isinstance(data["tts"], dict):
            self.tts = data["tts"].copy()
        if "stt" in data and isinstance(data["stt"], dict):
            self.stt = data["stt"].copy()
        if "llm" in data and isinstance(data["llm"], dict):
            self.llm = data["llm"].copy()
        if "modules" in data and isinstance(data["modules"], dict):
            self.modules = data["modules"].copy()
        
        # Activation config
        if "activation" in data and isinstance(data["activation"], dict):
            a = data["activation"]
            self.activation.enabled = bool(a.get("enabled", self.activation.enabled))
            self.activation.server_url = str(a.get("server_url", self.activation.server_url))
            self.activation.check_interval_hours = int(a.get("check_interval_hours", self.activation.check_interval_hours))
            self.activation.offline_grace_days = int(a.get("offline_grace_days", self.activation.offline_grace_days))
        
        # Startup config
        if "startup" in data and isinstance(data["startup"], dict):
            s = data["startup"]
            self.startup.run_on_system_start = bool(s.get("run_on_system_start", self.startup.run_on_system_start))
            self.startup.auto_start_client = bool(s.get("auto_start_client", self.startup.auto_start_client))
        
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
                "auto_hide_on_client_start": self.window.auto_hide_on_client_start,
                "minimize_to_tray": self.window.minimize_to_tray,
            },
            "paths": {
                "client_root": self.paths.client_root,
                "models_dir": self.paths.models_dir,
                "logs_dir": self.paths.logs_dir,
                "client_logs_dir": self.paths.client_logs_dir,
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
                "temperature": self.ollama.temperature,
            },
            "ollama_server": {
                "url": self.ollama_server.url,
                "launch_mode": self.ollama_server.launch_mode,
                "bind_address": self.ollama_server.bind_address,
                "allow_external": self.ollama_server.allow_external,
                "auto_restart": self.ollama_server.auto_restart,
            },
            "api_keys": {
                "server_api_key": self.api_keys.server_api_key,
                "weather_api_key": self.api_keys.weather_api_key,
                "news_api_key": self.api_keys.news_api_key,
                "search_api_key": self.api_keys.search_api_key,
                "search_engine_id": self.api_keys.search_engine_id,
            },
            "logging": {
                "level": self.logging.level,
                "max_size_mb": self.logging.max_size_mb,
                "backup_count": self.logging.backup_count,
                "file_logging": self.logging.file_logging,
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
            "activation": {
                "enabled": self.activation.enabled,
                "server_url": self.activation.server_url,
                "check_interval_hours": self.activation.check_interval_hours,
                "offline_grace_days": self.activation.offline_grace_days,
            },
            # Preserve subsystem configs (if migration populated them)
            "tts": self.tts,
            "stt": self.stt,
            "llm": self.llm,
            "modules": self.modules,
            "startup": {
                "run_on_system_start": self.startup.run_on_system_start,
                "auto_start_client": self.startup.auto_start_client,
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

    def get(self, key: str, default=None):
        """Get a config value by dotted key (compatibility with client Config API)."""
        # Build a dict representation similar to save()
        data = {
            "window": {
                "width": self.window.width,
                "height": self.window.height,
                "x": self.window.x,
                "y": self.window.y,
                "auto_hide_on_client_start": self.window.auto_hide_on_client_start,
                "minimize_to_tray": self.window.minimize_to_tray,
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
                "temperature": self.ollama.temperature,
            },
            "user": {"name": self.user.name, "city": self.user.city},
            "languages": {"ui": self.languages.ui, "speech": self.languages.speech},
            "voice_models": {
                "stt_model": self.voice_models.stt_model,
                "tts_engine": self.voice_models.tts_engine,
                "tts_model": self.voice_models.tts_model,
                "tts_voice": self.voice_models.tts_voice,
            },
            "activation": {
                "enabled": self.activation.enabled,
                "server_url": self.activation.server_url,
                "check_interval_hours": self.activation.check_interval_hours,
                "offline_grace_days": self.activation.offline_grace_days,
            },
            "tts": self.tts,
            "stt": self.stt,
            "llm": self.llm,
            "modules": self.modules,
            "startup": {
                "run_on_system_start": self.startup.run_on_system_start,
                "auto_start_client": self.startup.auto_start_client,
            },
            "autoscroll_logs": self.autoscroll_logs,
            "language": self.languages.ui,
            "first_run": self.first_run,
            "installed_version": self.installed_version,
            "migration_done": self.migration_done,
        }

        # Support dotted key lookup
        parts = key.split(".") if key else []
        node = data
        for p in parts:
            if isinstance(node, dict) and p in node:
                node = node[p]
            else:
                return default
        return node
    
    def set(self, key: str, value) -> None:
        """Set a config value by dotted key (compatibility with client Config API)."""
        parts = key.split(".") if key else []
        
        if not parts:
            return
        
        # Handle top-level keys that map to dataclass attributes
        if len(parts) == 1:
            attr_name = parts[0]
            if hasattr(self, attr_name):
                setattr(self, attr_name, value)
            return
        
        # Handle nested keys like "tts.engine" or "voice_models.tts_engine"
        top_level = parts[0]
        
        # Map shorthand to full attribute names
        attr_map = {
            "tts": "tts",
            "stt": "stt",
            "llm": "llm",
            "modules": "modules",
            "voice_models": "voice_models",
        }
        
        if top_level in attr_map:
            attr_name = attr_map[top_level]
            if not hasattr(self, attr_name) or not isinstance(getattr(self, attr_name), dict):
                return
            
            target_dict = getattr(self, attr_name)
            sub_key = ".".join(parts[1:])
            target_dict[sub_key] = value

