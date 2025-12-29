"""
Environment variables loader for Arvis
"""

import os
from pathlib import Path
from typing import Any, Dict, Optional


class EnvLoader:
    """Load environment variables from .env file"""

    def __init__(self, env_file: str = ".env"):
        self.env_file = Path(env_file)
        self.env_vars = {}
        self.load_env()

    def load_env(self):
        """Load environment variables from .env file"""
        if not self.env_file.exists():
            print(f"Warning: {self.env_file} not found. Using default values.")
            return

        try:
            with open(self.env_file, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()

                    # Skip empty lines and comments
                    if not line or line.startswith("#"):
                        continue

                    # Parse key=value pairs
                    if "=" in line:
                        key, value = line.split("=", 1)
                        key = key.strip()
                        value = value.strip()

                        # Remove quotes if present
                        if value.startswith('"') and value.endswith('"'):
                            value = value[1:-1]
                        elif value.startswith("'") and value.endswith("'"):
                            value = value[1:-1]

                        # Set environment variable
                        os.environ[key] = value
                        self.env_vars[key] = value

            print(f"Loaded {len(self.env_vars)} environment variables from {self.env_file}")

        except Exception as e:
            print(f"Error loading .env file: {e}")

    def get(self, key: str, default: Any = None) -> Any:
        """Get environment variable with optional default"""
        value = os.environ.get(key, default)

        # Convert string values to appropriate types
        if isinstance(value, str):
            if value.lower() in ("true", "false"):
                return value.lower() == "true"
            elif value.isdigit():
                return int(value)
            elif value.replace(".", "", 1).isdigit() and value.count(".") == 1:
                # Only convert to float if there's exactly one decimal point
                return float(value)

        return value

    def get_api_keys(self) -> Dict[str, str]:
        """Get all API keys"""
        return {
            "weather": self.get("WEATHER_API_KEY", ""),
            "news": self.get("NEWS_API_KEY", ""),
            "search": self.get("GOOGLE_SEARCH_API_KEY", self.get("SEARCH_API_KEY", "")),
        }

    def get_search_settings(self) -> Dict[str, Any]:
        """Get web search integration settings"""
        engine_id = self.get("GOOGLE_SEARCH_ENGINE_ID", "")
        if not engine_id:
            engine_id = self.get("SEARCH_ENGINE_ID", "")
        enabled = self.get("GOOGLE_SEARCH_ENABLED", self.get("SEARCH_ENABLED", True))
        return {"engine_id": engine_id, "enabled": bool(enabled) if not isinstance(enabled, bool) else enabled}

    def get_user_settings(self) -> Dict[str, str]:
        """Get user settings"""
        return {"name": self.get("USER_NAME", "Пользователь"), "city": self.get("USER_CITY", "Киев")}

    def get_llm_settings(self) -> Dict[str, Any]:
        """Get LLM settings"""
        return {
            "ollama_url": self.get("OLLAMA_URL", self.get("OLLAMA_HOST", "http://localhost:11434")),
            "default_model": self.get("DEFAULT_LLM_MODEL", "auto"),
            "temperature": self.get("LLM_TEMPERATURE", 0.7),
            "max_tokens": self.get("LLM_MAX_TOKENS", 2048),
        }

    def get_tts_settings(self) -> Dict[str, Any]:
        """Get TTS settings"""
        return {
            "voice": self.get("TTS_VOICE", "ru_v3"),
            "sample_rate": self.get("TTS_SAMPLE_RATE", 48000),
            "device": self.get("TTS_DEVICE", "cpu"),
        }

    def get_stt_settings(self) -> Dict[str, str]:
        """Get STT settings"""
        return {
            "model_path": self.get("STT_MODEL_PATH", "models/vosk-model-ru-0.42"),
            "wake_word": self.get("WAKE_WORD", "арвис"),
        }

    def get_module_settings(self) -> Dict[str, bool]:
        """Get module enable/disable settings"""
        return {
            "weather_enabled": self.get("WEATHER_MODULE_ENABLED", True),
            "news_enabled": self.get("NEWS_MODULE_ENABLED", True),
            "system_control_enabled": self.get("SYSTEM_CONTROL_ENABLED", True),
            "calendar_enabled": self.get("CALENDAR_MODULE_ENABLED", True),
            "voice_activation_enabled": self.get("VOICE_ACTIVATION_ENABLED", True),
        }

    def get_paths(self) -> Dict[str, str]:
        """Get application paths"""
        return {
            "logs": self.get("LOGS_PATH", "logs"),
            "models": self.get("MODELS_PATH", "models"),
            "temp": self.get("TEMP_PATH", "temp"),
            "data": self.get("DATA_PATH", "data"),
        }

    def is_debug_mode(self) -> bool:
        """Check if debug mode is enabled"""
        return self.get("DEBUG_MODE", False)
