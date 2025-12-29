@echo off
chcp 65001 > nul
title Диагностика системы Arvis

echo ===============================================
echo         ДИАГНОСТИКА СИСТЕМЫ ARVIS
echo ===============================================
echo.

echo [1/7] Проверка ресурсов системы...
for /f "tokens=2 delims==" %%a in ('wmic cpu get loadpercentage /value ^| findstr "LoadPercentage"') do set cpu=%%a
for /f "tokens=2 delims==" %%a in ('wmic OS get FreePhysicalMemory /value ^| findstr "FreePhysicalMemory"') do set freemem=%%a
set /a freemem_gb=%freemem%/1024/1024
echo CPU загрузка: %cpu%%%
echo Свободно RAM: %freemem_gb% GB

echo.
echo [2/7] Проверка Python...
python --version > nul 2>&1
if %errorlevel% == 0 (
    echo ✅ Python найден
    python --version
) else (
    echo ❌ Python не найден
)

echo.
echo [3/7] Проверка виртуального окружения...
if exist "venv\Scripts\activate.bat" (
    echo ✅ Виртуальное окружение существует
    call venv\Scripts\activate.bat
    python -c "import PyQt6; print('✅ PyQt6 установлен')" 2>nul || echo "❌ PyQt6 не установлен"
    python -c "import requests; print('✅ Requests установлен')" 2>nul || echo "❌ Requests не установлен"
    python -c "import torch; print('✅ PyTorch установлен')" 2>nul || echo "❌ PyTorch не установлен"
) else (
    echo ❌ Виртуальное окружение не найдено
)

echo.
echo [4/7] Проверка Ollama процесса...
tasklist | findstr "ollama" > nul
if %errorlevel% == 0 (
    echo ✅ Ollama процесс запущен
) else (
    echo ❌ Ollama процесс не найден
    echo ℹ️  Теперь запуск Ollama выполняется через start_arvis.bat
    echo     Он откроет отдельное окно "Ollama Server" и выполнит: ollama serve
    echo     Либо вручную откройте отдельное окно cmd и выполните: ollama serve
)

echo.
echo [5/7] Тестирование Ollama API...
curl -s --max-time 5 http://localhost:11434/api/tags > nul
if %errorlevel% == 0 (
    echo ✅ Ollama API отвечает
    echo Список моделей:
    ollama list 2>nul || echo "Нет установленных моделей"
) else (
    echo ❌ Ollama API не отвечает
    echo    Убедитесь, что окно "Ollama Server" открыто и команда ollama serve запущена
)

echo.
echo [6/7] Проверка файловой структуры...
if exist "main.py" (echo ✅ main.py найден) else (echo ❌ main.py не найден)
if exist "config\config.json" (echo ✅ config.json найден) else (echo ❌ config.json не найден)
if exist "models" (echo ✅ Папка models существует) else (echo ❌ Папка models не найдена)
if exist "logs" (echo ✅ Папка logs существует) else (echo ❌ Папка logs не найдена)

echo.
echo [7/7] Проверка свободного места...
for /f "tokens=3" %%a in ('dir /-c %~dp0 ^| find "bytes free"') do set freespace=%%a
set /a freespace_gb=%freespace%/1024/1024/1024
echo Свободно на диске: %freespace_gb% GB

echo.
echo ===============================================
echo              РЕЗУЛЬТАТ ДИАГНОСТИКИ
echo ===============================================

if %cpu% GTR 80 echo ⚠️  Высокая загрузка CPU: %cpu%%%
if %freemem_gb% LSS 2 echo ⚠️  Мало свободной RAM: %freemem_gb% GB

echo.
echo 💡 Рекомендации:
echo • Закройте лишние приложения
echo • Убедитесь в наличии 4GB+ свободной RAM
echo • Используйте SSD для лучшей производительности
echo • Добавьте папку Arvis в исключения антивируса

echo.
set /p test="Запустить тестовый режим Arvis? (y/n): "
if /i "%test%"=="y" (
    echo.
    echo 🚀 Запуск Arvis в тестовом режиме...
    echo ===============================================
    python main.py
)

pause
