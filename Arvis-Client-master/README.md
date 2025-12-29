# Arvis AI Assistant - Client

Desktop voice assistant with offline STT/TTS, LLM integration, and comprehensive security.

## Quick Start

1. Install Python 3.11 or 3.12
2. Run setup: ```INSTALL.bat```
3. Start Arvis: ```LAUNCH.bat```
4. Login: 
   - Username: ```admin```
   - Password: ```Admin123!@#```

## Documentation

📖 **[Полный индекс документации](docs/INDEX.md)**

Быстрые ссылки:
- [User Management Guide](docs/user-guide/USER_MANAGEMENT_GUIDE.md)
- [2FA Setup](docs/user-guide/USER_GUIDE_2FA.md)
- [Technical Architecture](docs/technical/HYBRID_ARCHITECTURE_DESIGN.md)

## Repository Structure

- **Arvis-Client** (this repo) - Desktop client application
- **Arvis-Server** - Authentication and user management server

## Features

- 🎙️ Offline voice recognition (Vosk)
- 🔊 Natural TTS (Silero)
- 🤖 LLM integration (Ollama)
- 🔐 RBAC + 2FA security
- 🌐 Remote server authentication
- 📊 System monitoring

### Bark TTS auto-setup (Windows-friendly)

На первом запуске Bark теперь работает через отдельный воркер-процесс и может автоматически установить необходимые зависимости (PyTorch CPU + bark-ml) без ручной настройки. Это избавляет конечного пользователя от правок окружения и проблем с DLL (например, c10.dll).

- Автоустановка включена по умолчанию.
- Её можно отключить через `config/config.json`:

```
{
  "tts": {
    "bark": {
      "auto_install": false
    }
  }
}
```

При отсутствии интернета автоустановка будет пропущена, и движок Bark будет отключён до следующей попытки.

## Server Connection

To connect to remote authentication server:

1. Set in ```config/config.json```:{
   "security": {
     "auth": {
       "use_remote_server": true,
       "server_url": "http://your-server:8000"
     }
   }
}

2. Server repository: https://github.com/Fat1ms/Arvis-Server

## Testing

### TTS Models Test
Проверка работы всех TTS движков (Silero, Bark, SAPI):
```bash
tests\run_tts_tests.bat
```

### System Status
Проверка статуса системы:
```bash
STATUS.bat
```

## License

MIT
