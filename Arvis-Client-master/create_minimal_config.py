import json

# Создаем новый валидный config.json на основе примера
config_template = {
    "app": {
        "name": "Arvis - AI Assistant",
        "version": "1.5.1",
        "debug": False
    },
    "security": {
        "auth": {
            "enabled": True,
            "require_login": True,
            "use_remote_server": True,
            "server_url": "http://192.168.0.107:8000",
            "strict_server_mode": False,
            "session_timeout_minutes": 60
        }
    },
    "llm": {
        "default_model": "mistral:7b",
        "ollama_url": "http://localhost:11434"
    },
    "stt": {
        "engine": "vosk"
    },
    "tts": {
        "engine": "silero"
    }
}

# Сохраняем минимальную конфигурацию
with open("config/config_minimal.json", "w", encoding="utf-8") as f:
    json.dump(config_template, f, indent=4, ensure_ascii=False)

print("✅ Created minimal config: config/config_minimal.json")
print("   You can rename it to config.json if needed")
