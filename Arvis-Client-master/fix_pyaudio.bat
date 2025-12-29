@echo off
setlocal EnableExtensions EnableDelayedExpansion
chcp 65001 > nul
title Исправление проблемы PyAudio

REM Опционально: не паузить в конце (удобно для запуска из терминала/CI)
set "NO_PAUSE="
if /i "%~1"=="--no-pause" set "NO_PAUSE=1"

echo ========================================
echo   ДИАГНОСТИКА ПРОБЛЕМЫ PYAUDIO
echo ========================================
echo.

REM ------------------------------------------------------------
REM Найти Python (предпочтительно внутри venv)
REM ------------------------------------------------------------
set "ROOT=%~dp0"
set "PYEXE="
set "SCRIPTS_DIR="

if exist "%ROOT%.venv\Scripts\python.exe" (
    set "PYEXE=%ROOT%.venv\Scripts\python.exe"
    set "SCRIPTS_DIR=%ROOT%.venv\Scripts"
) else if exist "%ROOT%venv\Scripts\python.exe" (
    set "PYEXE=%ROOT%venv\Scripts\python.exe"
    set "SCRIPTS_DIR=%ROOT%venv\Scripts"
) else (
    set "PYEXE=python"
)

"%PYEXE%" --version > nul 2>&1
if errorlevel 1 (
    echo ❌ Python не найден.
    echo.
    echo Установите Python 3.11 или 3.12 - рекомендуется - и/или создайте venv через INSTALL.bat.
    echo https://python.org
    if not defined NO_PAUSE pause
    exit /b 1
)

REM Получаем версию и major/minor (без вложенного python -c в for /f, чтобы избежать ошибок парсинга cmd)
for /f "tokens=2 delims= " %%V in ('"%PYEXE%" --version 2^>^&1') do set "PYTHON_VERSION=%%V"
for /f "tokens=1,2 delims=." %%A in ("%PYTHON_VERSION%") do (
    set "PY_MAJOR=%%A"
    set "PY_MINOR=%%B"
)

echo ✅ Python найден: %PYTHON_VERSION%
if not "%SCRIPTS_DIR%"=="" (
    echo ✅ Используем venv: %SCRIPTS_DIR%
) else (
    echo ⚠️  Venv не найден, используется системный Python из PATH
)
echo.

REM ------------------------------------------------------------
REM Python 3.13: PyAudio часто несовместим / нет готовых колёс
REM ------------------------------------------------------------
if "%PY_MAJOR%"=="3" if "%PY_MINOR%"=="13" (
    echo ⚠️  Обнаружен Python 3.13 - НЕСОВМЕСТИМ с PyAudio!
    echo.
    echo 📋 Доступные решения:
    echo.
    echo 1. РЕКОМЕНДУЕТСЯ: Переустановить Python 3.11 или 3.12
    echo 2. Попробовать pipwin - предкомпилированные колёса
    echo 3. Установить wheel вручную: lfd.uci.edu
    echo 4. Работать без PyAudio - только текстовый режим
    echo.
    set /p CHOICE="Выберите вариант 1-4: "

    if "%CHOICE%"=="1" (
        echo.
        echo 📖 Инструкция:
        echo 1. Удалите Python 3.13 через "Установка и удаление программ"
        echo 2. Скачайте Python 3.11.9 или 3.12.x с https://www.python.org/downloads/
        echo 3. Удалите папку venv: rmdir /s /q venv
        echo 4. Запустите INSTALL.bat заново
        echo.
        echo 🔗 Подробнее: docs\PYTHON_313_COMPATIBILITY.md
        start https://www.python.org/downloads/
        if not defined NO_PAUSE pause
        exit /b 0
    )

    if "%CHOICE%"=="2" (
        echo.
        echo Установка через pipwin...
        "%PYEXE%" -m pip install --upgrade pip setuptools wheel
        "%PYEXE%" -m pip install --upgrade pipwin
        if errorlevel 1 (
            echo ❌ Не удалось установить pipwin.
            if not defined NO_PAUSE pause
            exit /b 1
        )
        if exist "%SCRIPTS_DIR%\pipwin.exe" (
            "%SCRIPTS_DIR%\pipwin.exe" install pyaudio
        ) else (
            "%PYEXE%" -m pipwin install pyaudio
        )
        "%PYEXE%" -c "import pyaudio" >nul 2>&1
        if errorlevel 1 (
            echo ❌ PyAudio не импортируется даже после pipwin.
            echo Попробуйте вариант 3 - wheel вручную - или установите Python 3.11/3.12.
            if not defined NO_PAUSE pause
            exit /b 1
        )
        echo ✅ PyAudio установлен и импортируется.
        if not defined NO_PAUSE pause
        exit /b 0
    )

    if "%CHOICE%"=="3" (
        echo.
        echo 📖 Установка wheel вручную:
        echo 1. Скачайте PyAudio wheel с:
        echo    https://www.lfd.uci.edu/~gohlke/pythonlibs/#pyaudio
        echo 2. Выберите wheel под вашу версию Python: cp313 и архитектуру: win_amd64
        echo 3. Установите - пример:
        echo    "%PYEXE%" -m pip install PyAudio-0.2.xx-cp313-cp313-win_amd64.whl
        echo.
        start https://www.lfd.uci.edu/~gohlke/pythonlibs/#pyaudio
        if not defined NO_PAUSE pause
        exit /b 0
    )

    if "%CHOICE%"=="4" (
        echo.
        echo 📖 Работа без PyAudio:
        echo.
        echo ✅ Будет работать:
        echo    - Текстовый ввод в чат
        echo    - LLM - Ollama
        echo    - TTS - озвучка ответов
        echo    - Все модули - погода, новости и т.д.
        echo.
        echo ❌ НЕ будет работать:
        echo    - Голосовой ввод - STT
        echo    - Wake word detection
        echo.
        echo Отключите голосовые функции в config.json:
        echo.
        echo   "stt": {
        echo     "enabled": false
        echo   },
        echo   "wake_word": {
        echo     "enabled": false
        echo   }
        echo.
        echo 🔗 Подробнее: docs\PYTHON_313_COMPATIBILITY.md
        if not defined NO_PAUSE pause
        exit /b 0
    )

    echo ❌ Неверный выбор
    if not defined NO_PAUSE pause
    exit /b 1
)

REM ------------------------------------------------------------
REM Python 3.11/3.12: ставим PyAudio в используемую среду
REM ------------------------------------------------------------
if "%PY_MAJOR%"=="3" if "%PY_MINOR%"=="11" goto :INSTALL_OK
if "%PY_MAJOR%"=="3" if "%PY_MINOR%"=="12" goto :INSTALL_OK
goto :OTHER_PY

:INSTALL_OK
    echo ✅ Python %PYTHON_VERSION% совместим с Arvis.
    echo.
    echo Попытка установки PyAudio...
    echo Обновление pip/setuptools/wheel...
    "%PYEXE%" -m pip install --upgrade pip setuptools wheel

    echo Установка PyAudio...
    echo Пробуем актуальную версию с готовыми wheel: 0.2.14
    "%PYEXE%" -m pip install --only-binary=:all: "pyaudio==0.2.14"
    if errorlevel 1 (
        echo ⚠️  Не удалось поставить PyAudio 0.2.14 через pip.
        echo Пробуем более старую версию: 0.2.13
        "%PYEXE%" -m pip install --only-binary=:all: "pyaudio==0.2.13"
    )

    if errorlevel 1 (
        echo ⚠️  Не удалось поставить PyAudio через pip.
        echo Пробуем fallback через pipwin - предкомпилированные колёса...
        "%PYEXE%" -m pip install --upgrade pipwin
        if errorlevel 1 (
            echo ❌ Не удалось установить pipwin.
            echo.
            echo Возможные причины:
            echo - отсутствует Visual C++ Redistributable
            echo - ограничения сети/антивирус
            echo.
            echo Попробуйте поставить VC++: https://aka.ms/vs/17/release/vc_redist.x64.exe
            if not defined NO_PAUSE pause
            exit /b 1
        )
        if exist "%SCRIPTS_DIR%\pipwin.exe" (
            "%SCRIPTS_DIR%\pipwin.exe" install pyaudio
        ) else (
            "%PYEXE%" -m pipwin install pyaudio
        )
        if errorlevel 1 (
            echo ❌ pipwin тоже не смог установить PyAudio.
            echo.
            echo Попробуйте:
            echo - установить VC++: https://aka.ms/vs/17/release/vc_redist.x64.exe
            echo - или wheel вручную: https://www.lfd.uci.edu/~gohlke/pythonlibs/#pyaudio
            if not defined NO_PAUSE pause
            exit /b 1
        )
    )

    echo.
    echo Проверка импорта...
    "%PYEXE%" -c "import pyaudio" >nul 2>&1
    if errorlevel 1 (
        echo ❌ PyAudio установлен, но не импортируется.
        echo Чаще всего помогает VC++ Redistributable:
        echo https://aka.ms/vs/17/release/vc_redist.x64.exe
        if not defined NO_PAUSE pause
        exit /b 1
    )

    echo ✅ PyAudio импортируется.

    echo.
    echo 🎉 Всё готово! Микрофон и wake word должны заработать.

    if not defined NO_PAUSE pause
    exit /b 0

:OTHER_PY

REM Другие версии Python
echo ⚠️  Python %PYTHON_VERSION% может быть несовместим
echo Рекомендуется Python 3.11 или 3.12
echo.
if not defined NO_PAUSE pause
exit /b 1
