@echo off
echo Starting WidgetForge Backend Services...

REM Start the main backend server
echo Starting FastAPI server...
start /B cmd /c "cd /d %~dp0 && uvicorn app.main:app --host 0.0.0.0 --port 8000"

REM Wait a bit for the server to start
timeout /t 5

REM Start the price poller (existing ticker data)
echo Starting MT5 Price Poller...
start /B cmd /c "cd /d %~dp0 && python app/pollers/poller_market.py"

REM Start the chart collector (new mini chart data)
echo Starting Chart Data Collector...
start /B cmd /c "cd /d %~dp0 && python app/pollers/chart_collector.py"

echo.
echo All services started!
echo.
echo FastAPI Server: http://localhost:8000
echo Price Ticker: http://localhost:8000/widgets/smooth-ticker
echo Mini Chart: http://localhost:8000/widgets/mini-chart?symbol=EURUSD
echo.
echo Press Ctrl+C to stop all services...
pause >nul