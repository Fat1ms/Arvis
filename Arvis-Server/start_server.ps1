# Arvis Auth Server Startup Script
# PowerShell version

$Host.UI.RawUI.WindowTitle = "Arvis Auth Server"
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Arvis Authentication Server" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

Set-Location $PSScriptRoot

if (-not (Test-Path "venv")) {
    Write-Host "[ERROR] Virtual environment not found!" -ForegroundColor Red
    Write-Host "Run: setup_server.bat" -ForegroundColor Yellow
    Write-Host ""
    Read-Host "Press Enter to exit"
    exit 1
}

Write-Host "Activating environment..." -ForegroundColor Yellow
& ".\venv\Scripts\Activate.ps1"

Write-Host "Checking dependencies..." -ForegroundColor Yellow
try {
    python -c "import uvicorn" 2>$null
    if ($LASTEXITCODE -ne 0) {
        throw "Dependencies not installed"
    }
} catch {
    Write-Host "[ERROR] Dependencies not installed!" -ForegroundColor Red
    Write-Host "Run: setup_server.bat" -ForegroundColor Yellow
    Write-Host ""
    Read-Host "Press Enter to exit"
    exit 1
}

$serverIP = (Get-NetIPAddress -AddressFamily IPv4 | Where-Object {$_.IPAddress -ne "127.0.0.1"} | Select-Object -First 1).IPAddress

Write-Host ""
Write-Host "========================================" -ForegroundColor Green
Write-Host "  Starting server..." -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host ""
Write-Host "Local:       http://localhost:8000" -ForegroundColor Cyan
Write-Host "Network:     http://${serverIP}:8000" -ForegroundColor Cyan
Write-Host "API docs:    http://${serverIP}:8000/docs" -ForegroundColor Cyan
Write-Host ""
Write-Host "Press Ctrl+C to stop" -ForegroundColor Yellow
Write-Host "========================================" -ForegroundColor Green
Write-Host ""

Set-Location ..
python -m uvicorn server.main:app --host 0.0.0.0 --port 8000
