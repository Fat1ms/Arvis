@echo off
chcp 65001 > nul
title Диагностика установки Arvis

echo ========================================
echo  ДИАГНОСТИКА УСТАНОВКИ ARVIS
echo ========================================
echo.

REM Создаём временный файл для лога
set LOG_FILE=setup_diagnostic_%date:~-4,4%%date:~-7,2%%date:~-10,2%_%time:~0,2%%time:~3,2%%time:~6,2%.log
set LOG_FILE=%LOG_FILE: =0%

echo Создание лога диагностики: %LOG_FILE%
echo. > %LOG_FILE%
echo ======================================== >> %LOG_FILE%
echo Диагностика установки Arvis >> %LOG_FILE%
echo Время: %date% %time% >> %LOG_FILE%
echo ======================================== >> %LOG_FILE%
echo. >> %LOG_FILE%

REM === 1. Проверка Python ===
echo [1/10] Проверка Python...
python --version > nul 2>&1
if %errorlevel% neq 0 (
    echo ❌ Python НЕ НАЙДЕН >> %LOG_FILE%
    echo ❌ Python НЕ НАЙДЕН!
    echo.
    echo 🔧 РЕШЕНИЕ:
    echo    1. Скачайте Python 3.11.9 или 3.12.x с https://python.org
    echo    2. При установке ОТМЕТЬТЕ "Add Python to PATH"
    echo    3. Перезагрузите компьютер
    echo    4. Запустите этот скрипт снова
    echo.
    goto :END
) else (
    for /f "tokens=2" %%i in ('python --version 2^>^&1') do set PYTHON_VERSION=%%i
    echo ✅ Python найден: %PYTHON_VERSION% >> %LOG_FILE%
    echo ✅ Python: %PYTHON_VERSION%
)

REM === 2. Проверка версии Python ===
echo [2/10] Проверка совместимости версии Python...
echo %PYTHON_VERSION% | findstr /C:"3.13" >nul
if %errorlevel% equ 0 (
    echo ⚠️  ПРЕДУПРЕЖДЕНИЕ: Python 3.13 >> %LOG_FILE%
    echo ⚠️  ВНИМАНИЕ: Python 3.13 НЕ ПОДДЕРЖИВАЕТСЯ!
    echo.
    echo 🔧 РЕШЕНИЕ:
    echo    1. Удалите Python 3.13
    echo    2. Установите Python 3.11.9 или 3.12.x
    echo    3. Запустите: rmdir /s /q venv
    echo    4. Запустите: setup_arvis.bat
    echo.
    echo 📖 Подробности: docs\PYTHON_313_COMPATIBILITY.md
    echo.
    set /p CONTINUE="Продолжить диагностику? (Y/N): "
    if /i not "%CONTINUE%"=="Y" goto :END
) else (
    echo ✅ Версия совместима >> %LOG_FILE%
    echo ✅ Версия совместима
)

REM === 3. Проверка pip ===
echo [3/10] Проверка pip...
python -m pip --version > nul 2>&1
if %errorlevel% neq 0 (
    echo ❌ pip не работает >> %LOG_FILE%
    echo ❌ pip не работает!
    echo.
    echo 🔧 РЕШЕНИЕ:
    echo    python -m ensurepip --default-pip
    echo.
    goto :END
) else (
    for /f "tokens=*" %%i in ('python -m pip --version 2^>^&1') do (
        echo ✅ %%i >> %LOG_FILE%
        echo ✅ %%i
    )
)

REM === 4. Проверка venv модуля ===
echo [4/10] Проверка модуля venv...
python -c "import venv" 2>nul
if %errorlevel% neq 0 (
    echo ❌ Модуль venv недоступен >> %LOG_FILE%
    echo ❌ Модуль venv недоступен!
    echo.
    echo 🔧 РЕШЕНИЕ:
    echo    Переустановите Python с опцией "pip" и "tcl/tk"
    echo.
    goto :END
) else (
    echo ✅ Модуль venv доступен >> %LOG_FILE%
    echo ✅ Модуль venv доступен
)

REM === 5. Проверка существующего venv ===
echo [5/10] Проверка виртуального окружения...
if exist "venv" (
    echo ✅ venv существует >> %LOG_FILE%
    echo ✅ venv существует

    REM Проверка работоспособности
    call venv\Scripts\activate.bat 2>nul
    if %errorlevel% equ 0 (
        python -c "print('test')" >nul 2>&1
        if %errorlevel% equ 0 (
            echo ✅ venv совместимо с текущим Python >> %LOG_FILE%
            echo ✅ venv совместимо
            echo.

            REM Проверка критичных пакетов В venv
            echo 📦 Проверка пакетов в venv:
            echo Проверка пакетов в venv: >> %LOG_FILE%

            python -c "import PyQt6; print('✅ PyQt6:', PyQt6.__version__)" 2>nul
            if %errorlevel% neq 0 (
                echo ❌ PyQt6 НЕ установлен в venv >> %LOG_FILE%
                echo ❌ PyQt6 НЕ установлен в venv
                set MISSING_PACKAGES=1
            ) else (
                for /f "tokens=*" %%i in ('python -c "import PyQt6; print('PyQt6:', PyQt6.__version__)" 2^>nul') do (
                    echo ✅ %%i >> %LOG_FILE%
                )
            )

            python -c "import requests; print('✅ Requests:', requests.__version__)" 2>nul
            if %errorlevel% neq 0 (
                echo ❌ Requests НЕ установлен в venv >> %LOG_FILE%
                echo ❌ Requests НЕ установлен в venv
                set MISSING_PACKAGES=1
            ) else (
                for /f "tokens=*" %%i in ('python -c "import requests; print('Requests:', requests.__version__)" 2^>nul') do (
                    echo ✅ %%i >> %LOG_FILE%
                )
            )

            python -c "import torch; print('✅ PyTorch:', torch.__version__)" 2>nul
            if %errorlevel% neq 0 (
                echo ❌ PyTorch НЕ установлен в venv >> %LOG_FILE%
                echo ❌ PyTorch НЕ установлен в venv
                set MISSING_PACKAGES=1
            ) else (
                for /f "tokens=*" %%i in ('python -c "import torch; print('PyTorch:', torch.__version__)" 2^>nul') do (
                    echo ✅ %%i >> %LOG_FILE%
                )
            )

            python -c "import vosk; print('✅ Vosk: OK')" 2>nul
            if %errorlevel% neq 0 (
                echo ⚠️  Vosk НЕ установлен в venv >> %LOG_FILE%
                echo ⚠️  Vosk НЕ установлен (опционально для STT)
            ) else (
                echo ✅ Vosk: OK >> %LOG_FILE%
            )

            if defined MISSING_PACKAGES (
                echo. >> %LOG_FILE%
                echo ❌ Критичные пакеты отсутствуют в venv! >> %LOG_FILE%
                echo.
                echo ❌ Критичные пакеты отсутствуют в venv!
                echo.
                echo 🔧 РЕШЕНИЕ:
                echo    quick_install_fix.bat
                echo    ИЛИ
                echo    install_packages_only.bat
                echo.
                echo 💡 Возможно, вы установили пакеты глобально
                echo    Они должны быть установлены ВНУТРИ venv!
                echo.
            ) else (
                echo ✅ Все критичные пакеты установлены >> %LOG_FILE%
                echo ✅ Все критичные пакеты установлены
            )

            REM Полный список пакетов в лог
            echo. >> %LOG_FILE%
            echo Полный список пакетов: >> %LOG_FILE%
            pip list >> %LOG_FILE% 2>&1
        ) else (
            echo ❌ venv НЕ совместимо с Python %PYTHON_VERSION% >> %LOG_FILE%
            echo ❌ venv НЕ совместимо!
            echo.
            echo 🔧 РЕШЕНИЕ:
            echo    1. Закройте все терминалы и редакторы
            echo    2. Запустите: fix_venv.bat
            echo    ИЛИ
            echo    1. rmdir /s /q venv
            echo    2. setup_arvis.bat
            echo.
        )
        call venv\Scripts\deactivate.bat 2>nul
    ) else (
        echo ❌ venv поврежден >> %LOG_FILE%
        echo ❌ venv поврежден!
        echo.
        echo 🔧 РЕШЕНИЕ: fix_venv.bat
        echo.
    )
) else (
    echo ⚠️  venv не создан >> %LOG_FILE%
    echo ⚠️  venv не создан - запустите setup_arvis.bat
)

REM === 6. Проверка прав доступа ===
echo [6/10] Проверка прав доступа...
echo test > temp_write_test.txt 2>nul
if exist "temp_write_test.txt" (
    echo ✅ Права на запись есть >> %LOG_FILE%
    echo ✅ Права на запись есть
    del temp_write_test.txt
) else (
    echo ❌ Недостаточно прав >> %LOG_FILE%
    echo ❌ Недостаточно прав!
    echo.
    echo 🔧 РЕШЕНИЕ:
    echo    Запустите этот скрипт от имени администратора
    echo.
)

REM === 7. Проверка места на диске ===
echo [7/10] Проверка места на диске...
for /f "tokens=3" %%a in ('dir %~d0 ^| findstr /C:"bytes free"') do set FREE_SPACE=%%a
echo Свободно на диске: %FREE_SPACE% байт >> %LOG_FILE%
echo ✅ Проверка места завершена

REM === 8. Проверка структуры папок ===
echo [8/10] Проверка структуры проекта...
set MISSING_FOLDERS=
if not exist "config" (
    echo ❌ Отсутствует папка: config >> %LOG_FILE%
    set MISSING_FOLDERS=%MISSING_FOLDERS% config
)
if not exist "modules" (
    echo ❌ Отсутствует папка: modules >> %LOG_FILE%
    set MISSING_FOLDERS=%MISSING_FOLDERS% modules
)
if not exist "src" (
    echo ❌ Отсутствует папка: src >> %LOG_FILE%
    set MISSING_FOLDERS=%MISSING_FOLDERS% src
)
if not exist "utils" (
    echo ❌ Отсутствует папка: utils >> %LOG_FILE%
    set MISSING_FOLDERS=%MISSING_FOLDERS% utils
)

if defined MISSING_FOLDERS (
    echo ❌ Отсутствуют папки:%MISSING_FOLDERS%
    echo.
    echo 🔧 РЕШЕНИЕ:
    echo    Скачайте полный проект с GitHub
    echo.
) else (
    echo ✅ Структура проекта корректна >> %LOG_FILE%
    echo ✅ Структура проекта корректна
)

REM === 9. Проверка requirements.txt и config.json ===
echo [9/10] Проверка конфигурации...

if exist "requirements.txt" (
    echo ✅ requirements.txt найден >> %LOG_FILE%
    echo ✅ requirements.txt найден
) else (
    echo ❌ requirements.txt НЕ найден >> %LOG_FILE%
    echo ❌ requirements.txt НЕ найден!
    echo.
    echo 🔧 РЕШЕНИЕ:
    echo    Скачайте requirements.txt с GitHub
    echo.
)

if exist "config\config.json" (
    echo ✅ config.json найден >> %LOG_FILE%
    echo ✅ config.json найден
) else (
    echo ❌ config.json НЕ найден >> %LOG_FILE%
    echo ❌ config.json НЕ найден!
    echo.
    echo 🔧 РЕШЕНИЕ:
    echo    create_config.bat
    echo    ИЛИ
    echo    copy config\config.json.example config\config.json
    echo.
)

REM === 10. Проверка Ollama ===
echo [10/10] Проверка Ollama...
where ollama > nul 2>&1
if %errorlevel% neq 0 (
    echo ⚠️  Ollama не установлен >> %LOG_FILE%
    echo ⚠️  Ollama не установлен
    echo.
    echo 💡 РЕКОМЕНДАЦИЯ:
    echo    1. Скачайте Ollama с https://ollama.ai
    echo    2. Установите и запустите
    echo    3. Выполните: ollama pull llama3.2
    echo.
) else (
    echo ✅ Ollama установлен >> %LOG_FILE%
    echo ✅ Ollama установлен

    tasklist | findstr "ollama" > nul
    if %errorlevel% neq 0 (
        echo ⚠️  Ollama не запущен >> %LOG_FILE%
        echo ⚠️  Ollama не запущен
        echo    Запустите: ollama serve
    ) else (
        echo ✅ Ollama работает >> %LOG_FILE%
        echo ✅ Ollama работает
    )
)

echo.
echo ========================================
echo     ДИАГНОСТИКА ЗАВЕРШЕНА
echo ========================================
echo.
echo 📄 Полный лог сохранён: %LOG_FILE%
echo.

:END
echo 🔧 Доступные решения:
echo    - quick_install_fix.bat       (быстрое исправление пакетов)
echo    - install_packages_only.bat   (установка только пакетов)
echo    - create_config.bat           (создать config.json)
echo    - setup_arvis.bat             (полная установка)
echo    - fix_venv.bat                (пересоздать venv)
echo    - fix_pyaudio.bat             (установить PyAudio)
echo.
echo 📖 Документация:
echo    - YOUR_CASE_FIX.md                        (для вашего случая!)
echo    - INSTALLATION_HELP.md                    (краткая помощь)
echo    - docs\SERVER_INSTALL_TROUBLESHOOTING.md  (полный гайд)
echo    - QUICK_FIX.md                            (шпаргалка)
echo.
pause
