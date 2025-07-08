@echo off
title WidgetForge - Starting...

echo Starting WidgetForge Backend...
echo.

cd /d "%~dp0"

echo [1/3] Starting API Server...
start "API Server" powershell -Command "uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload"

timeout /t 3 >nul

echo [2/3] Starting Price Collector...  
start "Price Collector" powershell -Command "python app/pollers/poller_market.py"

timeout /t 3 >nul

echo [3/3] Starting Chart Collector...
start "Chart Collector" powershell -Command "python app/pollers/chart_collector.py"

echo.
echo WidgetForge started! Opening browser...
start http://localhost:8000

echo.
echo All services running. You can close this window.
pause