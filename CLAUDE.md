# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview
WidgetForge Backend is a MetaTrader 5 (MT5) trading terminal management system that provides real-time trading data collection, widget generation, and market data streaming for up to 9 MT5 trading terminals.

## Development Commands

### Running the Application
```bash
cd backend
uvicorn app.main:app --reload
```

### Installing Dependencies
```bash
cd backend
pip install -r requirements.txt
```

### Testing
```bash
# Test cache functionality
cd backend
python tests/test_cache.py

# Test MT5 connection
python app/pollers/test_connection.py --terminal-id <ID> --login <LOGIN> --password <PASSWORD> --server <SERVER>
```

## Architecture Overview

### Core Components
1. **FastAPI Application** (`app/main.py`): Main entry point with routers for MT5 operations, terminal management, and WebSocket streaming
2. **Terminal Management**: Dual system architecture:
   - Legacy: `services/mt5_manager.py` (single-process, uses `logins.json`)
   - Production: `services/mt5_terminal_manager.py` (multi-process, encrypted storage)
3. **Polling System**: Each MT5 terminal runs in a separate subprocess (`pollers/terminal_poller.py`) polling every 5 seconds
4. **Caching Layer**: DiskCache-based caching in `/.cache` directory with different TTLs for various data types

### Key Design Patterns
- **Process Isolation**: Each MT5 terminal runs in its own Python subprocess to prevent API conflicts
- **Cache-First**: All data cached before serving to clients
- **WebSocket Streaming**: Real-time price updates at `/ws/price-stream`
- **Template-Based Widgets**: Server-side rendered HTML widgets using Jinja2

### Important Paths
- MT5 Terminals: `C:/MT5Terminals/Account{2-10}`
- Cache Directory: `/.cache` (relative to project root)
- Environment File: `C:/WidgetForge/widgetforge-backend/.env`
- Terminal Config: `.cache/mt5_terminals.json`
- Encryption Key: `.cache/mt5_key.key`

### API Authentication
- Admin endpoints require `X-API-Key` header matching the `API_KEY` environment variable
- WebSocket connections don't require authentication

### Data Flow
1. Terminal pollers collect data from MT5 terminals every 5 seconds
2. Data is cached using DiskCache with appropriate TTLs
3. API endpoints serve data from cache
4. WebSocket broadcasts price updates every second
5. Widgets fetch data via JavaScript from API endpoints

## Important Notes
- Windows-specific implementation with hardcoded paths
- Terminals must be pre-installed at specific locations (Account2-Account10)
- Password encryption uses Fernet symmetric encryption
- No automated tests or linting configuration currently exists