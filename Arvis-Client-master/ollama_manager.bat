@echo off
setlocal EnableExtensions
chcp 65001 > nul
title Управление Ollama (упрощённый режим)

echo ========================================
echo        УПРАВЛЕНИЕ OLLAMA
echo ========================================
echo.

REM Поддержка CLI: start | stop | status
if /I "%~1"=="start" goto start_ollama
if /I "%~1"=="stop" goto stop_ollama
if /I "%~1"=="status" goto check_status

:menu
echo Выберите действие:
echo 1. Запустить Ollama (отдельное окно)
echo 2. Остановить Ollama
echo 3. Проверить статус
echo 0. Выход
echo.
set /p choice="Ваш выбор (0-3): "
if "%choice%"=="1" goto start_ollama
if "%choice%"=="2" goto stop_ollama
if "%choice%"=="3" goto check_status
if "%choice%"=="0" goto exit
goto menu

:start_ollama
echo 🚀 Открываю отдельное окно "Ollama Server"...
start "Ollama Server" cmd /k "ollama serve"
echo Если окно не появилось, убедитесь что ollama установлена и доступна в PATH.
echo.
if "%~1"=="start" goto exit
pause
goto menu

:stop_ollama
echo 🛑 Остановка Ollama процесса...
taskkill /f /im "ollama.exe" >nul 2>&1
if %errorlevel%==0 (
    echo ✅ Процесс ollama.exe остановлен
) else (
    echo ❌ Процесс ollama.exe не найден
)
echo.
if "%~1"=="stop" goto exit
pause
goto menu

:check_status
echo 🔍 Проверка статуса Ollama...
tasklist | findstr /I "ollama.exe" > nul
if %errorlevel%==0 (
    echo ✅ Процесс: ЗАПУЩЕН
) else (
    echo ❌ Процесс: НЕ НАЙДЕН
)
curl -s --max-time 3 http://127.0.0.1:11434/api/version > nul 2>&1
if %errorlevel%==0 (
    echo ✅ API: ОТВЕЧАЕТ (http://127.0.0.1:11434)
) else (
    echo ❌ API: НЕ ОТВЕЧАЕТ
)
echo.
if "%~1"=="status" goto exit
pause
goto menu

:exit
echo.
echo Готово.
endlocal & exit /b 0
