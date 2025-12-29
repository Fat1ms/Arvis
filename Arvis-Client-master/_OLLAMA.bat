@echo off
chcp 65001 > nul
title Управление Ollama
cd /d "%~dp0"

:menu
cls
echo ========================================
echo       УПРАВЛЕНИЕ OLLAMA SERVER
echo ========================================
echo.
echo 1. Запустить Ollama
echo 2. Остановить Ollama
echo 3. Проверить статус
echo 4. Установить модель (llama3.2)
echo 5. Список моделей
echo 6. Удалить модель
echo 7. Выход
echo.
set /p choice="Выберите действие (1-7): "

if "%choice%"=="1" goto start
if "%choice%"=="2" goto stop
if "%choice%"=="3" goto status
if "%choice%"=="4" goto install
if "%choice%"=="5" goto list
if "%choice%"=="6" goto remove
if "%choice%"=="7" goto exit
goto menu

:start
echo.
echo Запуск Ollama...
tasklist | findstr "ollama" >nul 2>&1
if %errorlevel% equ 0 (
    echo ✅ Ollama уже запущен
) else (
    start "Ollama Server" cmd /k "ollama serve"
    timeout /t 3 /nobreak >nul
    echo ✅ Ollama запущен в отдельном окне
)
pause
goto menu

:stop
echo.
echo Остановка Ollama...
taskkill /F /IM ollama.exe >nul 2>&1
if %errorlevel% equ 0 (
    echo ✅ Ollama остановлен
) else (
    echo ⚠️  Ollama не был запущен
)
pause
goto menu

:status
echo.
echo Проверка статуса Ollama...
tasklist | findstr "ollama" >nul 2>&1
if %errorlevel% equ 0 (
    echo ✅ Процесс Ollama запущен
    python -c "import requests; r=requests.get('http://127.0.0.1:11434/api/version', timeout=2); print(f'✅ API доступен: v{r.json().get(\"version\", \"unknown\")}')" 2>nul
    if %errorlevel% neq 0 (
        echo ⚠️  API не отвечает
    )
) else (
    echo ❌ Ollama не запущен
)
echo.
pause
goto menu

:install
echo.
echo Установка модели llama3.2...
echo (Это может занять несколько минут)
echo.
ollama pull llama3.2
if %errorlevel% equ 0 (
    echo ✅ Модель llama3.2 установлена
) else (
    echo ❌ Ошибка установки модели
)
pause
goto menu

:list
echo.
echo Список установленных моделей:
ollama list
echo.
pause
goto menu

:remove
echo.
ollama list
echo.
set /p model="Введите название модели для удаления: "
if "%model%"=="" (
    echo ❌ Название модели не указано
) else (
    ollama rm %model%
    if %errorlevel% equ 0 (
        echo ✅ Модель %model% удалена
    ) else (
        echo ❌ Ошибка удаления модели
    )
)
pause
goto menu

:exit
exit
