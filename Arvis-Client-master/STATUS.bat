@echo off
chcp 65001 > nul
title Arvis Status Check
cd /d "%~dp0"

echo ========================================
echo      ARVIS SYSTEM STATUS CHECK
echo ========================================
echo.

REM Python
echo [1/6] Python...
python --version 2>nul
if %errorlevel% neq 0 (
    echo [FAIL] Python not found
) else (
    for /f "tokens=2" %%i in ('python --version 2^>^&1') do echo [OK] Python %%i
)
echo.

REM Virtual Environment
echo [2/6] Virtual environment...
set "VENV_DIR="
if exist ".venv\Scripts\python.exe" set "VENV_DIR=.venv"
if "%VENV_DIR%"=="" if exist "venv\Scripts\python.exe" set "VENV_DIR=venv"

if not "%VENV_DIR%"=="" (
    echo [OK] Virtual environment exists: %VENV_DIR%
    call %VENV_DIR%\Scripts\activate.bat 2>nul
    if %errorlevel% equ 0 (
        echo [OK] Environment activates
    ) else (
        echo [WARN] Activation problem
    )
) else (
    echo [FAIL] Virtual environment not found
    echo Run: INSTALL.bat
)
echo.

REM Dependencies
echo [3/6] Dependencies...
if not "%VENV_DIR%"=="" (
    %VENV_DIR%\Scripts\python.exe -c "import PyQt6" 2>nul && echo [OK] PyQt6 || echo [FAIL] PyQt6
    %VENV_DIR%\Scripts\python.exe -c "import requests" 2>nul && echo [OK] requests || echo [FAIL] requests
    %VENV_DIR%\Scripts\python.exe -c "import vosk" 2>nul && echo [OK] vosk || echo [FAIL] vosk
    %VENV_DIR%\Scripts\python.exe -c "import torch" 2>nul && echo [OK] torch || echo [FAIL] torch
    %VENV_DIR%\Scripts\python.exe -c "import pyaudio" 2>nul && echo [OK] pyaudio || echo [WARN] pyaudio not detected - audio features limited
)
echo.

REM Ollama
echo [4/6] Ollama...
tasklist | findstr "ollama" >nul 2>&1
if %errorlevel% equ 0 (
    echo [OK] Ollama process running
    python -c "import requests; r=requests.get('http://127.0.0.1:11434/api/version', timeout=2); print('[OK] Ollama API available at http://127.0.0.1:11434')" 2>nul
    if %errorlevel% neq 0 (
        echo [WARN] Ollama running but API not responding
    )
) else (
    echo [FAIL] Ollama not running
    echo Install from https://ollama.ai
)
echo.

REM Configuration
echo [5/6] Configuration...
if exist "config\config.json" (
    echo [OK] config\config.json
) else (
    echo [WARN] config\config.json not found
)
if exist "main.py" (
    echo [OK] main.py
) else (
    echo [FAIL] main.py not found
)
echo.

REM Folders
echo [6/6] Folder structure...
if exist "logs" (echo [OK] logs\) else (echo [WARN] logs\ && mkdir logs)
if exist "models" (echo [OK] models\) else (echo [WARN] models\ && mkdir models)
if exist "data" (echo [OK] data\) else (echo [WARN] data\ && mkdir data)
if exist "temp" (echo [OK] temp\) else (echo [WARN] temp\ && mkdir temp)

echo.
echo ========================================
echo.
echo COMMANDS:
echo    INSTALL.bat     - reinstall Arvis
echo    LAUNCH.bat      - start Arvis
echo    DIAGNOSTIC.bat  - extended diagnostics
echo.
pause
