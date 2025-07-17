@echo off
title WidgetForge Backend - Desktop Launcher
color 0A
cls

REM Change to the backend directory (handles being launched from anywhere)
cd /d "%~dp0"

REM Check if we're in the right location
if not exist "app\main.py" (
    echo ❌ ERROR: Cannot find WidgetForge Backend files!
    echo    Expected location: %~dp0
    echo    Please check the installation path.
    pause
    exit /b 1
)

echo.
echo  ██╗    ██╗██╗██████╗  ██████╗ ███████╗████████╗███████╗ ██████╗ ██████╗  ██████╗ ███████╗
echo  ██║    ██║██║██╔══██╗██╔════╝ ██╔════╝╚══██╔══╝██╔════╝██╔═══██╗██╔══██╗██╔════╝ ██╔════╝
echo  ██║ █╗ ██║██║██║  ██║██║  ███╗█████╗     ██║   █████╗  ██║   ██║██████╔╝██║  ███╗█████╗  
echo  ██║███╗██║██║██║  ██║██║   ██║██╔══╝     ██║   ██╔══╝  ██║   ██║██╔══██╗██║   ██║██╔══╝  
echo  ╚███╔███╔╝██║██████╔╝╚██████╔╝███████╗   ██║   ██║     ╚██████╔╝██║  ██║╚██████╔╝███████╗
echo   ╚══╝╚══╝ ╚═╝╚═════╝  ╚═════╝ ╚══════╝   ╚═╝   ╚═╝      ╚═════╝ ╚═╝  ╚═╝ ╚═════╝ ╚══════╝
echo.
echo                             🚀 Windows Server 2019 VPS Production 🚀
echo.
echo ================================================================================
echo.
echo 📍 Location: %CD%
echo 🖥️  Server: Windows Server 2019 VPS
echo 📅 Date: %DATE% %TIME%
echo.
echo 🔄 Launching WidgetForge Backend Services...
echo.

REM Small delay for dramatic effect
timeout /t 2 /nobreak >nul

REM Launch the production script
call "scripts\production\start-all-services.bat"

REM Keep this window open briefly to show completion
echo.
echo 🎉 WidgetForge Backend launched successfully!
echo.
echo 💡 You can now minimize this window - services are running independently.
echo.
timeout /t 5 /nobreak >nul