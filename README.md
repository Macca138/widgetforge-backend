# WidgetForge Backend

A MetaTrader 5 (MT5) trading terminal management system that provides real-time trading data collection, widget generation, and market data streaming. Deployed on **Windows Server 2019 VPS**.

## Quick Start

### Production (Windows Server 2019)
```powershell
cd backend
# Start all services via PowerShell
START_WIDGETFORGE.bat

# Or directly
scripts\production\start-all-services.bat
```

### Development
```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload
```

## Features

- **Real-time Price Data**: MT5 market data polling and WebSocket streaming
- **Mini Chart Widgets**: Historical price charts with live updates
- **Market Tickers**: Customizable price tickers for streaming
- **Economic Calendar**: Forex Factory calendar integration
- **Widget System**: Server-side rendered HTML widgets

## Architecture

The system uses a dual architecture:

1. **Price Data System**: Independent MT5 connection for market data (mini charts, tickers, price widgets)
2. **Authentication System**: Role-based access control for traders and admins (under development)

## Documentation

- [`/docs/architecture/`](docs/architecture/) - System architecture and design documents
- [`/docs/api/`](docs/api/) - API integration plans and specifications
- [`/CLAUDE.md`](CLAUDE.md) - Development instructions and project context

## Development

See [`CLAUDE.md`](CLAUDE.md) for detailed development instructions and project context.

## License

Private project for 5ers Prop Firm integration.