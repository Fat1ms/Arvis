@echo off
chcp 65001 > nul
echo.
echo ═══════════════════════════════════════════════════════════
echo   🔍 АВТОМАТИЧЕСКАЯ ДИАГНОСТИКА СЕРВЕРА ARVIS
echo ═══════════════════════════════════════════════════════════
echo.
echo Этот скрипт проверит состояние сервера и поможет найти проблему
echo.
pause
echo.

echo ═══════════════════════════════════════════════════════════
echo   1️⃣  IP АДРЕС СЕРВЕРА
echo ═══════════════════════════════════════════════════════════
ipconfig | findstr IPv4
echo.

echo ═══════════════════════════════════════════════════════════
echo   2️⃣  ПРОЦЕССЫ PYTHON
echo ═══════════════════════════════════════════════════════════
powershell -Command "Get-Process | Where-Object {$_.ProcessName -like '*python*'} | Format-Table ProcessName,Id,CPU -AutoSize"
echo.

echo ═══════════════════════════════════════════════════════════
echo   3️⃣  ПОРТ 8000 - СОСТОЯНИЕ
echo ═══════════════════════════════════════════════════════════
netstat -ano | findstr :8000
echo.
echo Должно быть: 0.0.0.0:8000 в состоянии LISTENING
echo НЕ должно быть: 127.0.0.1:8000
echo.

echo ═══════════════════════════════════════════════════════════
echo   4️⃣  FIREWALL - ПРАВИЛА ДЛЯ ПОРТА 8000
echo ═══════════════════════════════════════════════════════════
netsh advfirewall firewall show rule name=all | findstr /C:"Arvis" /C:"8000"
echo.

echo ═══════════════════════════════════════════════════════════
echo   5️⃣  ТЕСТ LOCALHOST (на самом сервере)
echo ═══════════════════════════════════════════════════════════
curl http://localhost:8000/health
echo.

echo ═══════════════════════════════════════════════════════════
echo   6️⃣  ТЕСТ IP АДРЕСА (на самом сервере)
echo ═══════════════════════════════════════════════════════════
curl http://192.168.0.130:8000/health
echo.

echo ═══════════════════════════════════════════════════════════
echo   7️⃣  ТЕСТ ЭНДПОИНТА РЕГИСТРАЦИИ
echo ═══════════════════════════════════════════════════════════
curl -X OPTIONS http://192.168.0.130:8000/api/client/register
echo.

echo ═══════════════════════════════════════════════════════════
echo   📊 АНАЛИЗ РЕЗУЛЬТАТОВ
echo ═══════════════════════════════════════════════════════════
echo.
echo Проверьте результаты выше:
echo.
echo ✅ Процессы Python найдены?
echo    - Если НЕТ → Сервер не запущен! Запустите: python main.py
echo.
echo ✅ Порт 8000 в состоянии LISTENING?
echo    - Если НЕТ → Сервер не слушает порт
echo    - Если 127.0.0.1:8000 → Измените host на "0.0.0.0" в main.py
echo.
echo ✅ Тест localhost работает (HTTP 200)?
echo    - Если НЕТ → Сервер не отвечает на запросы
echo    - Если ДА → Проблема в сети или firewall
echo.
echo ✅ Тест IP работает (HTTP 200)?
echo    - Если НЕТ, но localhost работает → Проблема в firewall
echo    - Выполните: netsh advfirewall firewall add rule name="Arvis Server" dir=in action=allow protocol=TCP localport=8000
echo.
echo ═══════════════════════════════════════════════════════════
echo   🆘 БЫСТРЫЕ РЕШЕНИЯ
echo ═══════════════════════════════════════════════════════════
echo.
echo ПРОБЛЕМА: Сервер не запущен
echo РЕШЕНИЕ: cd C:\path\to\Arvis-Server ^&^& python main.py
echo.
echo ПРОБЛЕМА: Слушает 127.0.0.1 вместо 0.0.0.0
echo РЕШЕНИЕ: В main.py измените uvicorn.run(app, host="0.0.0.0", port=8000)
echo.
echo ПРОБЛЕМА: Firewall блокирует
echo РЕШЕНИЕ: netsh advfirewall firewall add rule name="Arvis Server" dir=in action=allow protocol=TCP localport=8000
echo.
echo ПРОБЛЕМА: Порт занят другим процессом
echo РЕШЕНИЕ: netstat -ano ^| findstr :8000 (найти PID), затем taskkill /PID <номер> /F
echo.
echo ═══════════════════════════════════════════════════════════
echo.
echo 📋 Сохраните этот вывод и отправьте команде клиента!
echo.
pause
