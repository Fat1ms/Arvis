@echo off
chcp 65001 > nul
title Arvis Installation
cd /d "%~dp0"

echo ========================================
echo     ARVIS AI ASSISTANT INSTALLATION
echo ========================================
echo.

REM Check Python
echo [1/6] Checking Python...
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ERROR: Python not found!
    echo.
    echo Install Python 3.11.9 or 3.12.x from https://python.org
    echo Check "Add Python to PATH" during installation
    echo.
    pause
    exit /b 1
)

echo OK: Python found
python --version
echo.

REM Check Python version
echo [2/6] Checking Python version...
for /f "tokens=2" %%i in ('python --version 2^>^&1') do set PYTHON_VERSION=%%i
echo Version: %PYTHON_VERSION%

echo %PYTHON_VERSION% | findstr /C:"3.13" >nul
if %errorlevel% equ 0 (
    echo.
    echo WARNING: Python 3.13 has limited support
    echo PyAudio may not work, Python 3.11 or 3.12 recommended
    echo.
    timeout /t 3 /nobreak >nul
)

REM Create virtual environment
echo.
echo [3/6] Creating virtual environment...
if exist "venv" (
    echo Removing old environment...
    rmdir /s /q venv 2>nul
    timeout /t 1 /nobreak >nul
)

python -m venv venv
if %errorlevel% neq 0 (
    echo ERROR: Failed to create virtual environment
    echo Try running as administrator
    pause
    exit /b 1
)
echo OK: Virtual environment created

REM Activate environment
echo.
echo [4/6] Activating environment...
call venv\Scripts\activate.bat
if %errorlevel% neq 0 (
    echo ERROR: Failed to activate environment
    pause
    exit /b 1
)

REM Update pip
echo.
echo [5/6] Updating pip...
python -m pip install --upgrade pip >nul 2>&1

REM Install dependencies
echo.
echo [6/6] Installing dependencies (5-10 minutes)...
echo    - Critical packages first...
pip install --upgrade pip setuptools wheel >nul 2>&1

echo    - PyQt6 GUI framework...
pip install PyQt6==6.7.1 PyQt6-sip==13.8.0 --no-warn-script-location
if %errorlevel% neq 0 (
    echo ERROR: PyQt6 installation failed!
    echo Try: 1) Update pip: python -m pip install --upgrade pip
    echo      2) Install Visual C++ Redistributable
    pause
    exit /b 1
)

echo    - PyQt6 additional components...
pip install PyQt6-Qt6 --no-warn-script-location 2>nul
if %errorlevel% equ 0 (
    echo OK: PyQt6-Qt6 installed
) else (
    echo WARNING: PyQt6-Qt6 skipped (optional)
)

echo    - Main packages...
pip install -r requirements.txt --no-warn-script-location
if %errorlevel% neq 0 (
    echo WARNING: Some packages failed, installing critical ones individually...
    
    echo    - Installing core packages...
    pip install requests soundfile numpy --no-warn-script-location
    
    echo    - Installing security packages...
    pip install pyotp qrcode Pillow pyjwt cryptography python-dateutil python-dotenv --no-warn-script-location
    echo OK: Security packages installed
    
    echo    - Installing system packages...
    pip install psutil pywin32 --no-warn-script-location
    
    echo    - Installing PyTorch (CPU version)...
    pip install torch torchaudio --index-url https://download.pytorch.org/whl/cpu --no-warn-script-location
    
    echo    - Installing TTS engines...
    pip install pyttsx3 --no-warn-script-location
    pip install bark-ml --no-warn-script-location 2>nul
    
    echo    - Installing Vosk (speech recognition)...
    pip install vosk srt --no-warn-script-location 2>nul
    if %errorlevel% neq 0 (
        echo WARNING: Vosk not available for your Python version
        echo          Speech recognition will be limited
    ) else (
        echo OK: Vosk installed successfully
    )
)

echo    - Verifying PyTorch installation...
python -c "import torch; print(torch.__version__)" >nul 2>&1
if %errorlevel% neq 0 (
    echo       PyTorch not detected, installing CPU build from official index...
    pip install torch torchaudio --index-url https://download.pytorch.org/whl/cpu --no-warn-script-location
    if %errorlevel% neq 0 (
        echo WARNING: Failed to install PyTorch automatically. Silero TTS will be unavailable until installed.
    ) else (
        echo OK: PyTorch installed (CPU)
    )
)

echo    - PyAudio (may fail on Python 3.13)...
pip install pyaudio >nul 2>&1
if %errorlevel% neq 0 (
    echo WARNING: PyAudio not installed - some audio features unavailable
) else (
    echo OK: PyAudio installed
)

echo.
echo [7/7] Pre-loading TTS models (Silero, Bark)...
echo    - Silero model (100-200MB)...
python -c "import torch; torch.hub.load('snakers4/silero-models', 'silero_tts', language='ru', speaker='v3_1_ru', verbose=False)" >nul 2>&1
if %errorlevel% neq 0 (
    echo WARNING: Silero model failed to load (will load on first use)
) else (
    echo OK: Silero preloaded
)

echo    - Bark model (optional, ~7GB - may take long time)...
echo    Skipping Bark pre-load. Will load on first use with lazy loading.
echo    To preload manually: python -c "import bark; bark.preload_models()"

REM Create folders
if not exist "logs" mkdir logs
if not exist "models" mkdir models
if not exist "data" mkdir data
if not exist "temp" mkdir temp

echo.
echo ========================================
echo        INSTALLATION COMPLETE!
echo ========================================
echo.
echo OK: Arvis is ready to use
echo.
echo TTS Configuration:
echo    Priority: Silero (fast) → Bark (quality) → SAPI (fallback)
echo.
echo NEXT STEPS:
echo    1. Install Ollama: https://ollama.ai
echo    2. Run: LAUNCH.bat
echo.
echo ADDITIONAL COMMANDS:
echo    STATUS.bat        - check system
echo    DIAGNOSTIC.bat    - troubleshooting
echo.
pause
