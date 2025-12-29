"""
Server startup script
Скрипт запуска сервера аутентификации
"""

import argparse
import sys
from pathlib import Path

# Добавляем родительскую директорию в path
sys.path.insert(0, str(Path(__file__).parent.parent))

import uvicorn

from server.config import get_settings


def main():
    parser = argparse.ArgumentParser(description="Arvis Authentication Server")
    parser.add_argument("--host", default=None, help="Host to bind (default: from config)")
    parser.add_argument("--port", type=int, default=None, help="Port to bind (default: from config)")
    parser.add_argument("--dev", action="store_true", help="Run in development mode with auto-reload")
    parser.add_argument("--workers", type=int, default=1, help="Number of worker processes")

    args = parser.parse_args()

    settings = get_settings()

    host = args.host or settings.server_host
    port = args.port or settings.server_port
    reload = args.dev or settings.server_reload

    print("=" * 60)
    print("🤖 Arvis Authentication Server")
    print("=" * 60)
    print(f"📍 Host: {host}")
    print(f"🔌 Port: {port}")
    print(f"🔄 Reload: {reload}")
    print(f"👷 Workers: {args.workers}")
    print(f"🗄️  Database: {settings.database_url}")
    print("=" * 60)

    uvicorn.run(
        "server.main:app",
        host=host,
        port=port,
        reload=reload,
        workers=args.workers if not reload else 1,  # Single worker in reload mode
        log_level="info",
    )


if __name__ == "__main__":
    main()
