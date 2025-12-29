@echo off
chcp 65001 > nul
title Диагностика Arvis
cd /d "%~dp0"

echo ========================================
echo      ДИАГНОСТИКА ARVIS SYSTEM
echo ========================================
echo.

REM Создаём файл отчёта
set REPORT=logs\diagnostic_report_%date:~-4,4%%date:~-7,2%%date:~-10,2%_%time:~0,2%%time:~3,2%%time:~6,2%.txt
set REPORT=%REPORT: =0%
if not exist "logs" mkdir logs

echo Отчёт о диагностике Arvis > %REPORT%
echo Дата: %date% %time% >> %REPORT%
echo. >> %REPORT%

echo 💾 Создание отчёта: %REPORT%
echo.

REM 1. Системная информация
echo [1/8] Системная информация...
echo ========== Системная информация ========== >> %REPORT%
systeminfo | findstr /C:"OS Name" /C:"OS Version" /C:"System Type" >> %REPORT%
echo. >> %REPORT%

REM 2. Python
echo [2/8] Python...
echo ========== Python ========== >> %REPORT%
python --version >> %REPORT% 2>&1
python -c "import sys; print(f'Executable: {sys.executable}')" >> %REPORT% 2>&1
python -c "import sys; print(f'Path: {sys.path}')" >> %REPORT% 2>&1
echo. >> %REPORT%

REM 3. Virtual Environment
echo [3/8] Виртуальное окружение...
echo ========== Virtual Environment ========== >> %REPORT%
if exist "venv\Scripts\python.exe" (
    echo venv exists >> %REPORT%
    venv\Scripts\python.exe --version >> %REPORT% 2>&1
    venv\Scripts\python.exe -c "import sys; print(f'Executable: {sys.executable}')" >> %REPORT% 2>&1
) else (
    echo venv NOT FOUND >> %REPORT%
)
echo. >> %REPORT%

REM 4. Установленные пакеты
echo [4/8] Установленные пакеты...
echo ========== Installed Packages ========== >> %REPORT%
if exist "venv\Scripts\pip.exe" (
    venv\Scripts\pip.exe list >> %REPORT% 2>&1
) else (
    echo pip not found in venv >> %REPORT%
)
echo. >> %REPORT%

REM 5. Импорты Python
echo [5/8] Проверка импортов...
echo ========== Python Imports Check ========== >> %REPORT%
if exist "venv\Scripts\python.exe" (
    venv\Scripts\python.exe -c "import PyQt6; print('PyQt6: OK')" >> %REPORT% 2>&1
    venv\Scripts\python.exe -c "import requests; print('requests: OK')" >> %REPORT% 2>&1
    venv\Scripts\python.exe -c "import vosk; print('vosk: OK')" >> %REPORT% 2>&1
    venv\Scripts\python.exe -c "import torch; print('torch: OK')" >> %REPORT% 2>&1
    venv\Scripts\python.exe -c "import numpy; print('numpy: OK')" >> %REPORT% 2>&1
    venv\Scripts\python.exe -c "import pyaudio; print('pyaudio: OK')" >> %REPORT% 2>&1
)
echo. >> %REPORT%

REM 6. Ollama
echo [6/8] Ollama...
echo ========== Ollama ========== >> %REPORT%
tasklist | findstr "ollama" >> %REPORT% 2>&1
python -c "import requests; r=requests.get('http://127.0.0.1:11434/api/version', timeout=2); print(f'Ollama API: {r.json()}')" >> %REPORT% 2>&1
echo. >> %REPORT%

REM 7. Файловая система
echo [7/8] Файловая система...
echo ========== File System ========== >> %REPORT%
echo Current directory: %cd% >> %REPORT%
dir /b >> %REPORT%
echo. >> %REPORT%
echo config\ >> %REPORT%
if exist "config" dir /b config >> %REPORT%
echo. >> %REPORT%

REM 8. Последние логи
echo [8/8] Последние логи...
echo ========== Recent Logs ========== >> %REPORT%
if exist "logs" (
    for /f %%f in ('dir /b /o-d logs\*.log 2^>nul') do (
        echo Last log file: logs\%%f >> %REPORT%
        echo --- Content (last 20 lines): --- >> %REPORT%
        powershell -Command "Get-Content logs\%%f -Tail 20" >> %REPORT% 2>&1
        goto :done_logs
    )
    :done_logs
) else (
    echo No logs found >> %REPORT%
)
echo. >> %REPORT%

REM Итоговый вывод
echo.
echo ========================================
echo         ДИАГНОСТИКА ЗАВЕРШЕНА
echo ========================================
echo.
echo 📄 Отчёт сохранён: %REPORT%
echo.
echo 🔍 РЕЗУЛЬТАТЫ:
type %REPORT% | findstr /C:"OK" /C:"ERROR" /C:"NOT FOUND" /C:"FAILED"
echo.
echo 💡 РЕКОМЕНДАЦИИ:
echo    • Если venv NOT FOUND → запустите _УСТАНОВКА.bat
echo    • Если пакеты не импортируются → переустановите зависимости
echo    • Если Ollama не работает → установите с https://ollama.ai
echo.
echo 📖 Полный отчёт в файле выше
echo.
pause
