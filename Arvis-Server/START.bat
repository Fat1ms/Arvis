@echo off
chcp 65001 >nul
title Arvis Server - Quick Start

REM ========================================
REM   Быстрый запуск сервера Arvis
REM   Quick start script
REM ========================================

cd /d "%~dp0"

echo.
echo ========================================
echo   Arvis Authentication Server  
echo ========================================
echo.
echo Starting server...
echo.
echo Local:  http://localhost:8000
echo API:    http://localhost:8000/docs
echo.

REM Запуск через venv Python напрямую
cd ..
server\venv\Scripts\python.exe -m uvicorn server.main:app --host 0.0.0.0 --port 8000

pause
