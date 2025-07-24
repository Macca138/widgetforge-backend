@echo off
title WidgetForge Backend - Service Launcher
color 0A
echo.
echo =========================================
echo  WidgetForge Backend - Service Launcher
echo =========================================
echo.
echo Starting all services in separate PowerShell terminals...
echo.

REM Get the backend directory (two levels up from scripts\production)
set "BACKEND_DIR=%~dp0..\.."
cd /d "%BACKEND_DIR%"

echo Current directory: %BACKEND_DIR%
echo.

REM Terminal 1: FastAPI Server
echo [1/4] Starting FastAPI Server...
start powershell -NoExit -Command "cd '%BACKEND_DIR%'; Write-Host 'FastAPI Server Terminal' -ForegroundColor Green; Write-Host 'Starting uvicorn server...' -ForegroundColor Yellow; uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload"

REM Wait 3 seconds between launches
timeout /t 3 /nobreak >nul

REM Terminal 2: Price Poller (existing ticker functionality)
echo [2/4] Starting Price Poller...
start powershell -NoExit -Command "cd '%BACKEND_DIR%'; Write-Host 'Price Poller Terminal' -ForegroundColor Cyan; Write-Host 'Starting price data collection...' -ForegroundColor Yellow; python app/pollers/poller_market.py"

REM Wait 3 seconds between launches
timeout /t 3 /nobreak >nul

REM Terminal 3: Chart Collector (new mini chart functionality)
echo [3/4] Starting Chart Collector...
start powershell -NoExit -Command "cd '%BACKEND_DIR%'; Write-Host 'Chart Collector Terminal' -ForegroundColor Magenta; Write-Host 'Starting chart data collection...' -ForegroundColor Yellow; python app/pollers/chart_collector.py"

REM Wait 3 seconds between launches
timeout /t 3 /nobreak >nul

REM Terminal 4: Forex Factory Calendar Poller (NEW - financial news calendar data)
echo [4/4] Starting Forex Factory Calendar Poller...
start powershell -NoExit -Command "cd '%BACKEND_DIR%'; Write-Host 'Forex Factory Calendar Poller Terminal' -ForegroundColor Yellow; Write-Host 'Starting financial calendar data collection...' -ForegroundColor Yellow; python app/pollers/forex_factory_poller.py"

echo.
echo =========================================
echo  All services started successfully!
echo =========================================
echo.
echo Services running:
echo   1. FastAPI Server         - http://localhost:8000
echo   2. Price Poller           - Market data collection
echo   3. Chart Collector        - Historical chart data
echo   4. Forex Factory Poller   - Financial calendar data
echo.
echo Available widgets:
echo   - Price Ticker:           http://localhost:8000/widgets/smooth-ticker
echo   - Mini Chart:             http://localhost:8000/widgets/mini-chart?symbol=EURUSD
echo   - Rotating Financial News: http://localhost:8000/widgets/rotating-financial-news
echo   - Rotating Asset:         http://localhost:8000/widgets/rotating-asset
echo   - Market Sessions:        http://localhost:8000/widgets/market-sessions
echo   - Admin Dashboard:        http://localhost:8000/admin/dashboard
echo   - Mini Chart Builder:     http://localhost:8000/admin/mini-chart-builder
echo.
echo To stop all services: Close all PowerShell windows
echo.
pause