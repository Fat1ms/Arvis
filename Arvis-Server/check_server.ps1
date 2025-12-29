# Диагностика сервера Arvis (PowerShell)
# PowerShell version of check_server.bat

$Host.UI.RawUI.WindowTitle = "Диагностика сервера Arvis"
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Диагностика сервера Arvis" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

Set-Location $PSScriptRoot

$allOk = $true

# [1/6] Проверка Python
Write-Host "[1/6] Проверка Python..." -ForegroundColor Yellow
try {
    $pythonVersion = python --version 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-Host "✓ $pythonVersion найден" -ForegroundColor Green
    } else {
        Write-Host "❌ Python не найден" -ForegroundColor Red
        Write-Host "   Установите Python 3.11 или 3.12" -ForegroundColor Yellow
        $allOk = $false
    }
} catch {
    Write-Host "❌ Python не найден" -ForegroundColor Red
    $allOk = $false
}

# [2/6] Проверка виртуального окружения
Write-Host ""
Write-Host "[2/6] Проверка виртуального окружения..." -ForegroundColor Yellow
if (Test-Path "venv") {
    Write-Host "✓ Виртуальное окружение существует" -ForegroundColor Green
} else {
    Write-Host "❌ Виртуальное окружение не найдено" -ForegroundColor Red
    Write-Host "   Запустите: setup_server.bat" -ForegroundColor Yellow
    $allOk = $false
}

# [3/6] Проверка зависимостей
Write-Host ""
Write-Host "[3/6] Проверка зависимостей..." -ForegroundColor Yellow
if (Test-Path "venv") {
    & ".\venv\Scripts\Activate.ps1"
    try {
        python -c "import fastapi, uvicorn, sqlalchemy" 2>$null
        if ($LASTEXITCODE -eq 0) {
            Write-Host "✓ Все зависимости установлены" -ForegroundColor Green
        } else {
            Write-Host "❌ Зависимости не установлены" -ForegroundColor Red
            Write-Host "   Запустите: setup_server.bat" -ForegroundColor Yellow
            $allOk = $false
        }
    } catch {
        Write-Host "❌ Зависимости не установлены" -ForegroundColor Red
        $allOk = $false
    }
}

# [4/6] Проверка структуры проекта
Write-Host ""
Write-Host "[4/6] Проверка структуры проекта..." -ForegroundColor Yellow
if (Test-Path "main.py") {
    Write-Host "✓ Структура проекта в порядке" -ForegroundColor Green
} else {
    Write-Host "❌ Файл main.py не найден" -ForegroundColor Red
    $allOk = $false
}

# [5/6] Проверка директорий
Write-Host ""
Write-Host "[5/6] Проверка директорий..." -ForegroundColor Yellow
if (-not (Test-Path "..\data")) {
    New-Item -ItemType Directory -Path "..\data" | Out-Null
}
if (-not (Test-Path "..\logs")) {
    New-Item -ItemType Directory -Path "..\logs" | Out-Null
}
Write-Host "✓ Директории готовы" -ForegroundColor Green

# [6/6] Проверка статуса сервера
Write-Host ""
Write-Host "[6/6] Проверка статуса сервера..." -ForegroundColor Yellow
$serverRunning = netstat -an | Select-String ":8000" | Select-String "LISTENING"
if ($serverRunning) {
    Write-Host "✓ Сервер запущен" -ForegroundColor Green
    Write-Host ""
    Write-Host "Проверка версии сервера..." -ForegroundColor Yellow
    $serverIP = (Get-NetIPAddress -AddressFamily IPv4 | Where-Object {$_.IPAddress -ne "127.0.0.1"} | Select-Object -First 1).IPAddress
    Write-Host ""
    try {
        $response = Invoke-RestMethod -Uri "http://localhost:8000/version" -ErrorAction Stop
        Write-Host "Версия сервера: $($response.version)" -ForegroundColor Cyan
        Write-Host "API версия: $($response.api_version)" -ForegroundColor Cyan
        Write-Host "Минимальная версия клиента: $($response.min_client_version)" -ForegroundColor Cyan
    } catch {
        Write-Host "⚠ Не удалось получить информацию о версии" -ForegroundColor Yellow
    }
} else {
    Write-Host "⚠ Сервер не запущен" -ForegroundColor Yellow
    Write-Host "  Запустите: start_server.ps1" -ForegroundColor Cyan
}

Write-Host ""
if ($allOk) {
    Write-Host "========================================" -ForegroundColor Green
    Write-Host "  ✓ Диагностика завершена" -ForegroundColor Green
    Write-Host "========================================" -ForegroundColor Green
} else {
    Write-Host "========================================" -ForegroundColor Red
    Write-Host "  ⚠ Обнаружены проблемы" -ForegroundColor Red
    Write-Host "========================================" -ForegroundColor Red
    Write-Host ""
    Write-Host "Для исправления запустите: setup_server.bat"
}
Write-Host ""

Read-Host "Нажмите Enter для выхода"
