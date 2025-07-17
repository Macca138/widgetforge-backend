# WidgetForge Backend Scripts

Organized collection of scripts for managing the WidgetForge Backend system.

## Directory Structure

### `/production/`
Production scripts for normal operations:
- `start-all-services.bat` - **Main production launcher** - Starts all services via PowerShell
- `stop-all-services.bat` - Stops all WidgetForge services

### `/utilities/`
Utility scripts for maintenance and troubleshooting:
- `troubleshoot-services.bat` - Comprehensive troubleshooting guide
- `trigger-weekly-update.py` - Manual Forex Factory calendar update
- `init-auth-db.py` - Initialize authentication database
- `reset-chart-db.py` - Reset corrupted chart database
- `reset-chart-db.bat` - Database reset launcher

### `/development/`
Development scripts for testing and debugging:
- `start-forex-factory-poller.bat` - Start only Forex Factory poller
- `start-chart-collector.bat` - Start only chart collector

## Quick Start

For normal production use:
```bash
# Windows Server 2019 VPS
cd backend
START_WIDGETFORGE.bat

# Or directly
scripts\production\start-all-services.bat
```

For troubleshooting:
```bash
scripts\utilities\troubleshoot-services.bat
```

## Script Dependencies

All scripts assume you're running from the `backend` directory and have:
- Python 3.8+ installed
- Required packages: `pip install -r requirements.txt`
- MetaTrader 5 installed at `C:/MT5Terminals/Account*/`

## Notes

- The main production script uses PowerShell for better terminal management
- All scripts are designed for Windows Server 2019 VPS environment
- Individual service scripts are useful for debugging specific components