@echo off
title WidgetForge Backend - Service Stopper
color 0C
echo.
echo ==========================================
echo  WidgetForge Backend - Service Stopper
echo ==========================================
echo.
echo Stopping all WidgetForge services...
echo.

REM Stop Python processes (chart collector and price poller)
echo Stopping Python services...
taskkill /f /im python.exe 2>nul
if %errorlevel% == 0 (
    echo   ✓ Python services stopped
) else (
    echo   ℹ No Python services found running
)

REM Stop uvicorn processes (FastAPI server)
echo Stopping FastAPI server...
taskkill /f /im uvicorn.exe 2>nul
if %errorlevel% == 0 (
    echo   ✓ FastAPI server stopped
) else (
    echo   ℹ No FastAPI server found running
)

REM Alternative: Stop by process name containing uvicorn
wmic process where "name='python.exe' and commandline like '%%uvicorn%%'" delete 2>nul

REM Close CMD/PowerShell windows with specific titles
echo Closing service terminals...
taskkill /fi "WindowTitle eq FastAPI Server*" /f 2>nul
taskkill /fi "WindowTitle eq Price Poller*" /f 2>nul
taskkill /fi "WindowTitle eq Chart Collector*" /f 2>nul

echo.
echo ==========================================
echo  All services stopped!
echo ==========================================
echo.
echo You can now safely restart services with:
echo   - start_all_services_powershell.bat
echo   - start_all_services_cmd.bat
echo.
pause