@echo off
title 🚀 WidgetForge Backend - Quick Start
color 0A
cls

echo.
echo  ███╗   ██╗██╗██████╗  ██████╗ ███████╗████████╗███████╗ ██████╗ ██████╗  ██████╗ ███████╗
echo  ██╔╝   ██║██║██╔══██╗██╔════╝ ██╔════╝╚══██╔══╝██╔════╝██╔═══██╗██╔══██╗██╔════╝ ██╔════╝
echo  ██║ █╗ ██║██║██║  ██║██║  ███╗█████╗     ██║   █████╗  ██║   ██║██████╔╝██║  ███╗█████╗  
echo  ██║███╗██║██║██║  ██║██║   ██║██╔══╝     ██║   ██╔══╝  ██║   ██║██╔══██╗██║   ██║██╔══╝  
echo  ╚███╔███╔╝██║██████╔╝╚██████╔╝███████╗   ██║   ██║     ╚██████╔╝██║  ██║╚██████╔╝███████╗
echo   ╚══╝╚══╝ ╚═╝╚═════╝  ╚═════╝ ╚══════╝   ╚═╝   ╚═╝      ╚═════╝ ╚═╝  ╚═╝ ╚═════╝ ╚══════╝
echo.
echo                               🚀 Quick Start Launcher 🚀
echo.
echo ================================================================================

REM Get the current directory (backend folder)
set "BACKEND_DIR=%~dp0"
cd /d "%BACKEND_DIR%"

echo 📁 Working Directory: %BACKEND_DIR%
echo.

REM Check if required files exist
echo 🔍 Checking system requirements...
if not exist "app\main.py" (
    echo ❌ ERROR: app\main.py not found! Make sure you're in the backend directory.
    pause
    exit /b 1
)

if not exist "app\pollers\poller_market.py" (
    echo ❌ ERROR: Price poller not found!
    pause
    exit /b 1
)

echo ✅ All required files found!
echo.

REM Start services
echo 🚀 Starting WidgetForge Backend Services...
echo.

REM Terminal 1: FastAPI Server
echo [1/3] 🌐 Starting FastAPI Server (Port 8000)...
start "WidgetForge API Server" powershell -NoExit -Command "cd '%BACKEND_DIR%'; $host.UI.RawUI.WindowTitle='🌐 WidgetForge API Server'; Write-Host '🌐 WidgetForge FastAPI Server' -ForegroundColor Green; Write-Host 'Server starting on http://localhost:8000' -ForegroundColor Yellow; Write-Host ''; uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload"

REM Wait between launches
timeout /t 3 /nobreak >nul

REM Terminal 2: Price Poller
echo [2/3] 📊 Starting Price Data Collector...
start "WidgetForge Price Poller" powershell -NoExit -Command "cd '%BACKEND_DIR%'; $host.UI.RawUI.WindowTitle='📊 WidgetForge Price Collector'; Write-Host '📊 WidgetForge Price Data Collector' -ForegroundColor Cyan; Write-Host 'Collecting real-time market data...' -ForegroundColor Yellow; Write-Host ''; python app/pollers/poller_market.py"

REM Wait between launches
timeout /t 3 /nobreak >nul

REM Terminal 3: Chart Collector
echo [3/3] 📈 Starting Chart Data Collector...
start "WidgetForge Chart Collector" powershell -NoExit -Command "cd '%BACKEND_DIR%'; $host.UI.RawUI.WindowTitle='📈 WidgetForge Chart Collector'; Write-Host '📈 WidgetForge Chart Data Collector' -ForegroundColor Magenta; Write-Host 'Collecting historical chart data...' -ForegroundColor Yellow; Write-Host ''; python app/pollers/chart_collector.py"

echo.
echo ================================================================================
echo                          ✅ ALL SERVICES STARTED SUCCESSFULLY! ✅
echo ================================================================================
echo.
echo 🌐 Server URL:     http://localhost:8000
echo.
echo 🎯 Available Widgets:
echo    💹 Smooth Ticker:     http://localhost:8000/widgets/smooth-ticker
echo    📊 Mini Chart:        http://localhost:8000/widgets/mini-chart?symbol=EURUSD
echo    🔄 Rotating Asset:    http://localhost:8000/widgets/rotating-asset
echo    🌍 Market Sessions:   http://localhost:8000/widgets/market-sessions
echo.
echo 🛠️  Admin Tools:
echo    📋 Dashboard:         http://localhost:8000/admin/dashboard  
echo    🔧 Chart Builder:     http://localhost:8000/admin/mini-chart-builder
echo.
echo ================================================================================
echo.
echo 💡 Tips:
echo    • Keep this window open to see startup status
echo    • Each service runs in its own PowerShell window
echo    • Close PowerShell windows to stop services
echo    • Check the individual service windows for logs
echo.
echo ⚠️  To stop all services: Close all PowerShell windows or press Ctrl+C in each
echo.
echo ================================================================================

REM Wait a moment then try to open browser
timeout /t 2 /nobreak >nul
echo 🌐 Opening browser to WidgetForge...
start http://localhost:8000

echo.
echo 🎉 WidgetForge is now running! Happy trading! 🎉
echo.
pause