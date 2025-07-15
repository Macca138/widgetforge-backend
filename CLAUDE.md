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

## Current Development Context (2024)

### System Redesign in Progress
The system is being redesigned to replace MT5 account data collection with 5ers API integration for live streaming widgets. Key changes:

1. **Authentication System Overhaul**: Moving from hardcoded admin login to proper user management with roles (trader/admin)
2. **Account Data Migration**: Replacing MT5 terminal polling with 5ers API calls for account data
3. **Architecture Simplification**: Removing multi-terminal complexity, keeping single terminal for price data only

### Critical Reference Documents
When working on this project, always reference these analysis documents:

1. **`/AUTHENTICATION_SYSTEM_DESIGN.md`**: Complete design for new role-based authentication system
   - User roles (trader/admin) and permissions
   - Database schema with user names for widget display
   - Authentication flow and security implementation
   - Phase-by-phase implementation plan

2. **`/MT5_COMPONENT_ANALYSIS.md`**: Analysis of MT5 components and their dependencies
   - Two independent MT5 systems: price data vs account data
   - Components safe to remove vs essential for price widgets
   - Mini chart and price widget dependencies
   - Cleanup safety checklist

3. **`/MT5_API_Project_Outline.md`**: Project outline for 5ers API integration
   - Technical requirements for 5ers API
   - Security considerations and implementation approach
   - Example API client code with safety measures

### Current Architecture Understanding

#### Two Independent MT5 Systems:
1. **Price Data System** (KEEP):
   - `pollers/poller_market.py` - Real-time price polling
   - `pollers/chart_collector.py` - Historical data for mini charts
   - `services/cache_service.py` - Price caching functions
   - WebSocket `/ws/price-stream` - Real-time price updates
   - Essential for mini charts, tickers, rotating charts

2. **Account Data System** (REMOVE/REPLACE):
   - `services/mt5_manager.py` - Legacy account manager
   - `services/mt5_terminal_manager.py` - Production account manager
   - `pollers/poller_accounts.py` - Account data polling
   - `pollers/terminal_poller.py` - Terminal-specific polling
   - Will be replaced with 5ers API calls

#### Current Admin Interface Structure:
- `admin_login.html` - Hardcoded login (to be replaced)
- `admin_dashboard.html` - Main dashboard with iframe navigation
- `admin_enhanced_account_builder.html` - Advanced account widget builder
- `admin_mt5_terminal_manager.html` - Terminal management (to be removed)
- `admin_ticker.html` - Market ticker builder

### Development Phases

#### Phase 1: Cleanup (Current)
- Remove account-only MT5 components
- Remove hardcoded authentication
- Simplify codebase structure

#### Phase 2: Authentication System
- Implement user management database
- Add role-based authentication (trader/admin)
- Create user management interface

#### Phase 3: Account Data Migration
- Implement 5ers API integration
- Create new account management interface
- Build API-based account widgets

#### Phase 4: Widget Updates
- Update widget builders for new authentication
- Implement account selection by trader names
- Add real-time account data streaming

### Security Considerations
- Current hardcoded password: "Alpha5ersDeliciousPool!" (to be removed)
- New system will use bcrypt password hashing
- Fernet encryption for investor passwords
- Role-based access control
- Server-side session management

### Key Insights for Future Development
- Price data widgets are completely independent of account data
- Mini charts use separate chart history database and market price poller
- WebSocket price streaming works independently of account terminals
- Widget builders need to display trader names instead of email addresses
- Admin role inherits all trader functions (can add own accounts)

### Testing Requirements
After any changes, always test:
- Mini chart widgets functionality
- Price WebSocket streaming
- Market ticker widgets
- Rotating asset widgets
- Chart history API endpoints