@echo off
echo Resetting Chart Database...
echo.

REM Stop chart collector if running
echo Stopping chart collector service...
taskkill /f /im python.exe /fi "WINDOWTITLE eq chart_collector*" 2>nul

REM Run the reset script
echo Running database reset script...
python reset_chart_db.py

echo.
echo Database reset complete!
echo.
echo To restart the chart collector:
echo 1. Run: python app/pollers/chart_collector.py
echo 2. Or restart all services: start_all_services.bat
echo.
pause