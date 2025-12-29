@echo off
chcp 65001 > nul
title Arvis AI Assistant
cd /d "%~dp0"

echo ========================================
echo      ARVIS AI ASSISTANT LAUNCH
echo ========================================
echo.

REM Check if venv exists, if yes - use it, if no - use system Python
set "VENV_ACTIVATE="
set "VENV_LABEL="

if exist ".venv\Scripts\activate.bat" set "VENV_ACTIVATE=.venv\Scripts\activate.bat" & set "VENV_LABEL=.venv"
if "%VENV_ACTIVATE%"=="" if exist "venv\Scripts\activate.bat" set "VENV_ACTIVATE=venv\Scripts\activate.bat" & set "VENV_LABEL=venv"

if not "%VENV_ACTIVATE%"=="" (
    echo OK: Activating virtual environment %VENV_LABEL%...
    call "%VENV_ACTIVATE%"
) else (
    echo OK: Using system Python - virtual environment not found
)

REM Check dependencies
echo Checking dependencies...
python -c "import PyQt6" 2>nul
if %errorlevel% neq 0 (
    echo ERROR: PyQt6 not installed!
    echo.
    echo Please run: pip install -r requirements.txt
    echo Or run: INSTALL.bat
    echo.
    pause
    exit /b 1
)

REM Start Ollama
echo Starting Ollama...
tasklist | findstr "ollama" >nul 2>&1
if %errorlevel% neq 0 (
    echo Starting Ollama in separate window...
    start "Ollama Server" cmd /k "ollama serve"
    timeout /t 5 /nobreak >nul
) else (
    echo OK: Ollama already running
)

REM Check Ollama availability
python -c "import requests; requests.get('http://127.0.0.1:11434/api/version', timeout=2)" 2>nul
if %errorlevel% neq 0 (
    echo WARNING: Ollama not responding
    echo AI features may be unavailable
    echo.
)

echo.
echo Starting Arvis GUI...
echo ========================================
echo.

python main.py

if %errorlevel% neq 0 (
    echo.
    echo ERROR: Arvis failed to start
    echo.
    echo For diagnostics run: diagnose_setup.bat
    echo Or check status: STATUS.bat
    echo Check logs in: logs\
    echo.
    pause
) else (
    echo.
    echo OK: Arvis closed correctly
)
