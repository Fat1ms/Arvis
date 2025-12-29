@echo off
chcp 65001 >nul
setlocal

REM =================================================================
REM ==                                                             ==
REM ==      ARVIS SERVER - UNIFIED MANAGEMENT SCRIPT               ==
REM ==      (Единый скрипт управления сервером Arvis)              ==
REM ==                                                             ==
REM =================================================================
REM ==                                                             ==
REM ==  Usage (Использование):                                     ==
REM ==    run.bat setup   - Install environment and dependencies   ==
REM ==    run.bat start   - Start the server                       ==
REM ==    run.bat check   - Check environment and server status    ==
REM ==    run.bat test    - Run API tests against a running server ==
REM ==                                                             ==
REM =================================================================

cd /d "%~dp0"

REM --- Parse command ---
if "%1"=="" (
    echo [ERROR] No command specified. Use 'setup', 'start', 'check', or 'test'.
    goto :eof
)
set "COMMAND=%1"

REM --- Route to the correct function ---
if /i "%COMMAND%"=="setup" goto :setup
if /i "%COMMAND%"=="start" goto :start
if /i "%COMMAND%"=="check" goto :check
if /i "%COMMAND%"=="test" goto :test

echo [ERROR] Unknown command: %COMMAND%
goto :eof


REM =================================================================
:setup
    title Arvis Server - Setup
    echo.
    echo [SETUP] Installing server environment...
    echo ========================================
    
    REM Check for Python
    python --version >nul 2>&1
    if errorlevel 1 (
        echo [ERROR] Python is not installed or not in PATH.
        echo Please install Python 3.11 or 3.12 from python.org
        goto :error_exit
    )

    REM Create virtual environment
    if not exist "venv" (
        echo [SETUP] Creating virtual environment...
        python -m venv venv
        if errorlevel 1 (
            echo [ERROR] Failed to create virtual environment.
            goto :error_exit
        )
    )

    echo [SETUP] Activating environment and installing dependencies...
    call venv\Scripts\activate.bat
    python -m pip install --upgrade pip >nul
    pip install -r requirements.txt
    if errorlevel 1 (
        echo [ERROR] Failed to install dependencies from requirements.txt.
        goto :error_exit
    )

    echo.
    echo [SUCCESS] Setup complete!
    echo You can now start the server with: run.bat start
    goto :success_exit


REM =================================================================
:start
    title Arvis Server - Running
    echo.
    echo [START] Starting Arvis Server...
    echo ========================================

    REM Check for venv
    if not exist "venv" (
        echo [ERROR] Virtual environment not found. Please run 'run.bat setup' first.
        goto :error_exit
    )
    call venv\Scripts\activate.bat

    REM Check for .env file
    if not exist ".env" (
        echo [WARNING] .env file not found. Copying from .env.example.
        copy .env.example .env
        echo [INFO] Please review and edit the .env file before production use.
    )

    echo [START] Launching Uvicorn server...
    echo Press Ctrl+C to stop the server.
    echo.
    
    python run_server.py
    goto :success_exit


REM =================================================================
:check
    title Arvis Server - Check
    echo.
    echo [CHECK] Performing diagnostics...
    echo ========================================

    REM Check Python
    python --version >nul 2>&1
    if errorlevel 1 (
        echo [FAIL] Python is not installed.
    ) else (
        echo [OK] Python is installed.
    )

    REM Check venv
    if not exist "venv" (
        echo [FAIL] Virtual environment not found. Run 'run.bat setup'.
    ) else (
        echo [OK] Virtual environment exists.
    )

    REM Check dependencies
    call venv\Scripts\activate.bat
    python -c "import fastapi, uvicorn" >nul 2>nul
    if errorlevel 1 (
        echo [FAIL] Core dependencies are not installed. Run 'run.bat setup'.
    ) else (
        echo [OK] Core dependencies are installed.
    )

    REM Check server status
    netstat -an | findstr :8000 | findstr LISTENING >nul
    if errorlevel 1 (
        echo [INFO] Server is not running.
    ) else (
        echo [OK] Server is running on port 8000.
    )
    echo.
    echo [SUCCESS] Check complete.
    goto :success_exit


REM =================================================================
:test
    title Arvis Server - API Test
    echo.
    echo [TEST] Running API tests...
    echo ========================================
    
    set "SERVER_URL=http://localhost:8000"
    
    echo [TEST] Checking server health at %SERVER_URL%/health...
    curl -s -o nul -w "%%{http_code}" "%SERVER_URL%/health" | findstr "200" >nul
    if errorlevel 1 (
        echo [FAIL] Server is not responding or unhealthy. Please start it with 'run.bat start'.
        goto :error_exit
    )
    echo [OK] Server is healthy.
    
    echo [TEST] Attempting to log in as admin...
    REM Note: This test assumes a default admin user exists.
    curl -s -X POST "%SERVER_URL%/api/auth/login" -H "Content-Type: application/json" -d "{\"username\":\"admin\",\"password\":\"%ADMIN_PASSWORD%\",\"device_name\":\"TestScript\"}" > test_output.json

    findstr /C:"access_token" test_output.json >nul
    if errorlevel 1 (
        echo [FAIL] Admin login failed. Check credentials or run init_users.py.
        type test_output.json
    ) else (
        echo [OK] Admin login successful.
    )
    del test_output.json >nul 2>&1
    echo.
    echo [SUCCESS] Test complete.
    goto :success_exit


REM =================================================================
:error_exit
    echo.
    pause
    exit /b 1

:success_exit
    echo.
    pause
    exit /b 0
