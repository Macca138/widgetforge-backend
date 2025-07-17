@echo off
echo Starting Chart Data Collector...
cd /d %~dp0
python app/pollers/chart_collector.py
pause