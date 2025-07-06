@echo off
title WidgetForge Backend - Service Launcher (CMD)
color 0A
echo.
echo ==========================================
echo  WidgetForge Backend - Service Launcher
echo ==========================================
echo.
echo Starting all services in separate CMD terminals...
echo.

REM Get the current directory (backend folder)
set "BACKEND_DIR=%~dp0"
cd /d "%BACKEND_DIR%"

echo Current directory: %BACKEND_DIR%
echo.

REM Terminal 1: FastAPI Server
echo [1/3] Starting FastAPI Server...
start "FastAPI Server" cmd /k "cd /d "%BACKEND_DIR%" && echo Starting FastAPI Server... && uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload"

REM Wait 3 seconds between launches
timeout /t 3 /nobreak >nul

REM Terminal 2: Price Poller (existing ticker functionality)
echo [2/3] Starting Price Poller...
start "Price Poller" cmd /k "cd /d "%BACKEND_DIR%" && echo Starting Price Data Collection... && python app/pollers/poller_market.py"

REM Wait 3 seconds between launches
timeout /t 3 /nobreak >nul

REM Terminal 3: Chart Collector (new mini chart functionality)
echo [3/3] Starting Chart Collector...
start "Chart Collector" cmd /k "cd /d "%BACKEND_DIR%" && echo Starting Chart Data Collection... && python app/pollers/chart_collector.py"

echo.
echo ==========================================
echo  All services started successfully!
echo ==========================================
echo.
echo Services running in separate windows:
echo   1. FastAPI Server    - http://localhost:8000
echo   2. Price Poller      - Market data collection
echo   3. Chart Collector   - Historical chart data
echo.
echo Available widgets:
echo   - Price Ticker:      http://localhost:8000/widgets/smooth-ticker
echo   - Mini Chart:        http://localhost:8000/widgets/mini-chart?symbol=EURUSD
echo   - Admin Dashboard:   http://localhost:8000/admin/dashboard
echo   - Mini Chart Builder: http://localhost:8000/admin/mini-chart-builder
echo.
echo To stop all services: Close all terminal windows
echo.
pause