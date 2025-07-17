@echo off
title WidgetForge Backend - Production Launcher
echo.
echo ==========================================
echo     WidgetForge Backend - Production
echo ==========================================
echo.
echo Starting production services...
echo.

REM Change to backend directory
cd /d "%~dp0"

REM Launch the production script
call "scripts\production\start-all-services.bat"