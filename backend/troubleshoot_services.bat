@echo off
title WidgetForge Backend - Troubleshoot Services
color 0E
echo.
echo ============================================
echo  WidgetForge Backend - Troubleshoot Guide
echo ============================================
echo.

REM Check if we're in the right directory
if not exist "app\main.py" (
    echo ❌ ERROR: Not in the correct backend directory!
    echo    Please run this script from the backend folder.
    echo    Expected path: C:\WidgetForge\widgetforge-backend\backend\
    pause
    exit /b 1
)

echo ✓ Running from correct directory: %CD%
echo.

echo === STEP 1: Check Python Installation ===
python --version 2>nul
if %errorlevel% neq 0 (
    echo ❌ Python not found! Install Python 3.8+ and add to PATH
    echo    Download from: https://python.org
) else (
    echo ✓ Python is installed
)

echo.
echo === STEP 2: Check Required Python Packages ===
python -c "import MetaTrader5; print('✓ MetaTrader5 package installed')" 2>nul || echo ❌ MetaTrader5 package missing - run: pip install MetaTrader5
python -c "import fastapi; print('✓ FastAPI package installed')" 2>nul || echo ❌ FastAPI package missing - run: pip install fastapi
python -c "import uvicorn; print('✓ Uvicorn package installed')" 2>nul || echo ❌ Uvicorn package missing - run: pip install uvicorn
python -c "import sqlite3; print('✓ SQLite3 built-in available')" 2>nul || echo ❌ SQLite3 not available

echo.
echo === STEP 3: Check MT5 Terminal Installation ===
if exist "C:\MT5Terminals\Account1\terminal64.exe" (
    echo ✓ MT5 Terminal found at C:\MT5Terminals\Account1\
) else (
    echo ❌ MT5 Terminal not found at expected location
    echo    Expected: C:\MT5Terminals\Account1\terminal64.exe
)

echo.
echo === STEP 4: Check Database Status ===
if exist "..\\.cache\\chart_history.db" (
    echo ✓ Chart history database exists
) else (
    echo ⚠ Chart history database not found (will be created automatically)
)

echo.
echo === STEP 5: Check Symbols File ===
if exist "app\\pollers\\symbols.txt" (
    echo ✓ Symbols file exists
    set /p symbolcount=< app\pollers\symbols.txt
    echo   First symbol: %symbolcount%
) else (
    echo ❌ Symbols file missing: app\pollers\symbols.txt
)

echo.
echo === STEP 6: Check Port Availability ===
netstat -an | findstr ":8000" >nul
if %errorlevel% == 0 (
    echo ⚠ Port 8000 is already in use - stop existing services first
) else (
    echo ✓ Port 8000 is available
)

echo.
echo === STEP 7: Quick Fixes ===
echo.
echo If you're having issues, try these solutions:
echo.
echo 1. MISSING PACKAGES:
echo    pip install -r requirements.txt
echo.
echo 2. CORRUPTED CHART DATABASE:
echo    reset_chart_db.bat
echo.
echo 3. PORT IN USE:
echo    stop_all_services.bat
echo.
echo 4. FRESH START:
echo    stop_all_services.bat
echo    reset_chart_db.bat
echo    start_all_services_powershell.bat
echo.
echo 5. PERMISSION ISSUES:
echo    Run as Administrator
echo.

echo ============================================
echo  Troubleshooting Complete
echo ============================================
echo.
pause