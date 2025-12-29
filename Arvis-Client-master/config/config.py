"""
Configuration management for Arvis
"""

import copy
import json
import os
from pathlib import Path
from typing import Any, Dict, Optional

from utils.env_loader import EnvLoader


class Config:
    def __init__(self, config_file: str = "config/config.json"):
        self.config_file = Path(config_file)
        self.env_loader = EnvLoader()
        self.config_data = self.load_config()

    def get_default_config(self):
        """Возвращает словарь с конфигурацией по умолчанию."""
        return {
            "language": {"ui": "ru", "tts": "ru", "stt": "ru"},
            "tts": {
                "engine": "silero",
                "speaker": "random",
                "use_local": True,
                "sample_rate": 48000,
                "device": "cpu",
                "preload": True,
                "enable_fallback": True,
                "bark_speaker": "v2/ru_speaker_5",
            },
            "stt": {"vosk_model_path": "models/vosk-model-small-ru-0.22", "mic_index": None},
            "llm": {
                "provider": "ollama",
                "model": "llama3:8b",
                "temperature": 0.7,
                "base_url": "http://127.0.0.1:11434",
                "assistant_engine": "ollama",
                "offline_mode": False,
                "providers": {
                    "search_priority": ["rss", "google_cse", "serpapi"],
                    "news_priority": ["rss", "gnews", "newsapi"],
                    "weather_priority": ["open_meteo", "openweathermap"]
                },
            },
            "startup": {"autostart_ollama": False, "autostart_server": False},
            "logging": {"level": "INFO", "max_size_mb": 10, "backup_count": 5},
            "modes": {
                "live_mode": False,
                "live_disable_wake_word": True,  # Отключать wake word детекцию в Live режиме
            },
            "user": {"username": "Guest", "role": "guest"},
            "api": {"server_url": "http://127.0.0.1:8000", "api_key": None},
        }

    def load_config(self):
        """Загружает конфигурацию из JSON-файла. Если файл не существует или некорректен,
        используется конфигурация по умолчанию."""
        config = self.get_default_config()

        if self.config_file.exists():
            try:
                with open(self.config_file, "r", encoding="utf-8") as f:
                    loaded_config = json.load(f)
                migrated = self._migrate_legacy_config(loaded_config, config)
                config = self._deep_update(config, migrated)
            except Exception as e:
                print(f"Error loading config: {e}")
                # Если произошла ошибка, создаем новый файл конфигурации с настройками по умолчанию
                self.save_config(config)
        else:
            # Создаем файл конфигурации с настройками по умолчанию, если он не существует
            self.save_config(config)

        return config

    def save_config(self, config_data: Optional[Dict[str, Any]] = None):
        """Сохраняет конфигурацию в JSON-файл."""
        if config_data is None:
            config_data = self.config_data

        # Создаем директорию для конфигурационного файла, если она не существует
        self.config_file.parent.mkdir(parents=True, exist_ok=True)

        try:
            with open(self.config_file, "w", encoding="utf-8") as f:
                json.dump(config_data, f, indent=4, ensure_ascii=False)
        except Exception as e:
            print(f"Error saving config: {e}")

    def get(self, key: str, default=None):
        """Получает значение конфигурации по ключу (поддерживает вложенные ключи через точку)"""
        keys = key.split(".")
        value = self.config_data

        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default

        return value

    def set(self, key: str, value: Any):
        """Устанавливает значение конфигурации по ключу (поддерживает вложенные ключи через точку)"""
        keys = key.split(".")
        config = self.config_data

        for k in keys[:-1]:
            if k not in config:
                config[k] = {}
            config = config[k]

        config[keys[-1]] = value
        self.save_config()

    def _deep_update(self, base: Dict[str, Any], updates: Dict[str, Any]) -> Dict[str, Any]:
        """Рекурсивно объединяет словари"""
        for key, value in updates.items():
            if isinstance(value, dict) and isinstance(base.get(key), dict):
                base[key] = self._deep_update(base[key], value)
            else:
                base[key] = value
        return base

    def _migrate_legacy_config(self, loaded_config: Dict[str, Any], default_config: Dict[str, Any]) -> Dict[str, Any]:
        """Применяет миграции для устаревших форматов конфигурации"""
        if not isinstance(loaded_config, dict):
            return {}

        migrated = copy.deepcopy(loaded_config)
        default_security = default_config.get("security", {})
        migrated = self._migrate_legacy_security(migrated, default_security)

        # Move legacy audit flag from security section
        security_section = migrated.get("security")
        audit_enabled_legacy = None
        if isinstance(security_section, dict) and "audit_enabled" in security_section:
            audit_enabled_legacy = security_section.pop("audit_enabled")

        audit_defaults = default_config.get("audit", {})
        if "audit" not in migrated:
            migrated["audit"] = copy.deepcopy(audit_defaults)
        elif isinstance(migrated["audit"], dict) and isinstance(audit_defaults, dict):
            migrated["audit"] = self._deep_update(copy.deepcopy(audit_defaults), migrated["audit"])

        if audit_enabled_legacy is not None and isinstance(migrated.get("audit"), dict):
            migrated["audit"]["enabled"] = bool(audit_enabled_legacy)

        return migrated

    def _migrate_legacy_security(self, config_data: Dict[str, Any], default_security: Dict[str, Any]) -> Dict[str, Any]:
        """Обновляет устаревший раздел безопасности до новой вложенной структуры"""
        security = config_data.get("security")

        if not isinstance(security, dict):
            config_data["security"] = copy.deepcopy(default_security)
            return config_data

        legacy_keys = {
            "auth_enabled",
            "2fa_enabled",
            "session_timeout_minutes",
            "allow_scripts",
            "settings_pin",
            "ollama_bind_address",
            "ollama_allow_external",
            "ollama_launch_mode",
            "require_login",
            "rbac_enabled",
            "default_role",
        }

        if any(key in security for key in legacy_keys):
            new_security = copy.deepcopy(default_security)

            new_security["auth"]["enabled"] = bool(security.get("auth_enabled", new_security["auth"]["enabled"]))
            new_security["auth"]["require_login"] = bool(
                security.get("require_login", new_security["auth"]["require_login"])
            )
            if "session_timeout_minutes" in security:
                new_security["auth"]["session_timeout_minutes"] = security.get("session_timeout_minutes")
            new_security["auth"]["two_factor"]["enabled"] = bool(
                security.get("2fa_enabled", new_security["auth"]["two_factor"]["enabled"])
            )

            if "allow_scripts" in security:
                new_security["execution"]["allow_scripts"] = bool(security.get("allow_scripts"))
            if "settings_pin" in security:
                new_security["settings"]["pin"] = security.get("settings_pin", "")
            if "ollama_bind_address" in security:
                new_security["ollama"]["bind_address"] = security["ollama_bind_address"]
            if "ollama_allow_external" in security:
                new_security["ollama"]["allow_external"] = bool(security["ollama_allow_external"])
            if "ollama_launch_mode" in security:
                new_security["ollama"]["launch_mode"] = str(security["ollama_launch_mode"]).lower()
            if "rbac_enabled" in security:
                new_security["rbac"]["enabled"] = bool(security["rbac_enabled"])
            if "default_role" in security:
                new_security["rbac"]["default_role"] = str(security["default_role"])

            config_data["security"] = new_security
        else:
            config_data["security"] = self._deep_update(copy.deepcopy(default_security), security)

        return config_data

    def get_ollama_models(self):
        """Get available LLM models"""
        return []

    def get_assistant_engine(self) -> str:
        """Return configured assistant engine name (e.g. 'ollama', 'heretic', 'remote')."""
        return str(self.get("llm.assistant_engine", self.get("llm.provider", "ollama")))

    def is_offline_mode(self) -> bool:
        """Whether Arvis should prefer offline providers and avoid remote calls by default."""
        return bool(self.get("llm.offline_mode", False))

    def get_search_provider_priority(self) -> list:
        val = self.get("llm.providers.search_priority", ["rss", "google_cse", "serpapi"])
        return val if isinstance(val, list) else ["rss", "google_cse", "serpapi"]

    def get_news_provider_priority(self) -> list:
        val = self.get("llm.providers.news_priority", ["rss", "gnews", "newsapi"])
        return val if isinstance(val, list) else ["rss", "gnews", "newsapi"]

    def get_weather_provider_priority(self) -> list:
        val = self.get("llm.providers.weather_priority", ["open_meteo", "openweathermap"])
        return val if isinstance(val, list) else ["open_meteo", "openweathermap"]

    def get_default_model(self):
        """Get default LLM model"""
        return self.get("llm.default_model", "auto")

    def get_ollama_url(self):
        """Get Ollama server URL"""
        return self.get("llm.ollama_url", "http://localhost:11434")

    def get_user_name(self):
        """Get user name"""
        return self.get("user.name", "Пользователь")

    def get_user_city(self):
        """Get user city"""
        return self.get("user.city", "Киев")

    # ---- Auth / Server getters ----
    def get_auth_server_url(self) -> str:
        return str(self.get("security.auth.server_url", "http://127.0.0.1:8000") or "http://127.0.0.1:8000")

    def is_remote_auth_enabled(self) -> bool:
        return bool(self.get("security.auth.use_remote_server", False))

    def is_remote_fallback_local(self) -> bool:
        return bool(self.get("security.auth.fallback_to_local", True))

    def is_auto_guest_on_failure(self) -> bool:
        return bool(self.get("security.auth.auto_login_guest_on_failure", False))

    def get_ollama_launch_mode(self) -> str:
        """Get configured launch mode for Ollama server."""
        try:
            launch_mode = self.get("security.ollama.launch_mode")
            if not launch_mode:
                launch_mode = self.get("startup.ollama_launch_mode")
            return str(launch_mode or "background").lower()
        except Exception:
            return "background"

    # ---- TTS Factory Methods (Days 4-5) ----
    def get_enabled_tts_engines(self) -> list:
        """Get list of enabled TTS engines.
        
        Returns:
            List of engine names that are enabled in config
        """
        engines = []
        try:
            engines_config = self.get("tts.engines", {})
            if engines_config:
                for engine_name, config in engines_config.items():
                    if isinstance(config, dict) and config.get("enabled", True):
                        engines.append(engine_name)
        except Exception:
            pass
        
        # Fallback to legacy config
        if not engines:
            engines = ["silero"]
        
        return engines

    def get_tts_engine_config(self, engine_type: str) -> Dict[str, Any]:
        """Get configuration for specific TTS engine.
        
        Args:
            engine_type: Engine type (e.g., "silero", "bark")
            
        Returns:
            Engine configuration dictionary
        """
        try:
            config = self.get(f"tts.engines.{engine_type}")
            return config if isinstance(config, dict) else {}
        except Exception:
            return {}

