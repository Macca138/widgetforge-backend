@echo off
echo Starting Forex Factory Calendar Poller...
cd /d %~dp0
python app/pollers/forex_factory_poller.py
pause