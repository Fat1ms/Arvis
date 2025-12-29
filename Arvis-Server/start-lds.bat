@echo off
REM Quick start script for LDS MVP (Windows)

setlocal enabledelayedexpansion

echo.
echo 🚀 Starting Arvis LDS MVP (Local Development)
echo ============================================== 
echo.

REM Check Docker
docker-compose --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Docker Compose not found. Install from https://docs.docker.com/compose/install/
    pause
    exit /b 1
)

REM Check environment file
if not exist .env (
    echo 📝 Creating .env from .env.development...
    copy .env.development .env
    echo ✅ .env created (edit for customization)
)

REM Start services
echo.
echo 🐳 Starting Docker containers (PostgreSQL, Redis, API)...
docker-compose up -d

REM Wait for services
echo ⏳ Waiting for services to be ready...
timeout /t 10 /nobreak

REM Initialize database
echo.
echo 📊 Initializing database schema...
docker-compose exec -T api python -m alembic upgrade head 2>nul || (
    echo ⚠️ Schema may already exist
)

REM Display endpoints
echo.
echo 📡 API is running at http://localhost:8000
echo.
echo 📚 Quick Start Commands:
echo.
echo 1️⃣  Register as Consumer:
echo    curl -X POST http://localhost:8000/auth/register ^
echo      -H "Content-Type: application/json" ^
echo      -d {\"email\":\"user@example.com\",\"password\":\"pass\",\"role\":\"consumer\"}
echo.
echo 2️⃣  View Logs:
echo    docker-compose logs -f api
echo.
echo 3️⃣  Stop Services:
echo    docker-compose down
echo.
echo 4️⃣  Access Database:
echo    docker-compose exec postgres psql -U arvis_lds -d arvis_lds
echo.
echo 📖 Full docs: ./lds/README.md
echo.
echo ✅ LDS MVP is ready! 🎉
echo.
pause
