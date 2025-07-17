# MT5 Component Analysis - Price Data vs Account Data

## Critical Discovery: Two Independent MT5 Systems

The WidgetForge backend uses **two completely separate MT5 systems**:

### 1. **Price Data System (Independent)**
- **Purpose**: Market data, mini charts, rotating charts, tickers
- **MT5 Connection**: Single connection for price polling only
- **No Account Access**: Only reads market prices, no account data
- **Components**: Completely separate from account management

### 2. **Account Data System (To Be Replaced)**
- **Purpose**: Trader account data (balance, equity, positions)
- **MT5 Connection**: Multiple terminals with account credentials
- **Account Access**: Full account information polling
- **Components**: Will be replaced with 5ers API

## Price Data System Components (ESSENTIAL - DO NOT REMOVE)

### **Core Price Polling**
- **File**: `/backend/app/pollers/poller_market.py`
- **Function**: Polls MT5 for real-time price data every 5 seconds
- **Data**: Current prices, spreads, percentage changes for all symbols
- **Cache**: `price:{symbol}` keys with 10-second expiration
- **MT5 Usage**: Read-only market data access (no account login required)

### **Chart History Collection**
- **File**: `/backend/app/pollers/chart_collector.py`
- **Function**: Collects historical price data for mini charts
- **Database**: `/.cache/chart_history.db` (SQLite)
- **Data**: 24 hours of 15-minute historical data, updated every 3 minutes
- **MT5 Usage**: Historical price data collection (no account access)

### **Price WebSocket Stream**
- **File**: `/backend/app/main.py` (lines 121-153)
- **Endpoint**: `/ws/price-stream`
- **Function**: Real-time price broadcasting to all widgets
- **Data**: Live price updates for all connected widgets
- **Dependencies**: Uses cached price data from market poller

### **Price API Endpoints**
- **File**: `/backend/app/main.py` (lines 113-118)
- **Endpoint**: `/price/{symbol}`
- **Function**: HTTP access to cached price data
- **Used by**: All price-based widgets for current prices

### **Chart History API**
- **File**: `/backend/app/routes/mt5_routes.py` (lines 197-273)
- **Endpoint**: `/api/mt5/chart-history/{symbol}`
- **Function**: Serves historical data for mini chart widgets
- **Data**: Historical price points for chart rendering

### **Price Cache Functions**
- **File**: `/backend/app/services/cache_service.py` (lines 9-14)
- **Functions**: `set_price()`, `get_price()`
- **Purpose**: Caches price data with 10-second expiration
- **Usage**: All price widgets access data through these functions

### **Symbol Configuration**
- **File**: `/backend/app/pollers/symbols.txt`
- **Content**: List of all symbols to poll (FOREX, indices, commodities, crypto)
- **Usage**: Defines which symbols are available for all widgets

## Account Data System Components (SAFE TO REMOVE)

### **Legacy Account Manager**
- **File**: `/backend/app/services/mt5_manager.py`
- **Purpose**: Manages MT5 terminal connections for account data
- **Data**: Account balance, equity, positions, trade history
- **MT5 Usage**: Full account login with credentials

### **Production Terminal Manager**
- **File**: `/backend/app/services/mt5_terminal_manager.py`
- **Purpose**: Multi-process account data collection
- **Features**: Encrypted password storage, process management
- **MT5 Usage**: Individual terminal processes with account access

### **Account Pollers**
- **Files**: 
  - `/backend/app/pollers/poller_accounts.py` (Legacy)
  - `/backend/app/pollers/terminal_poller.py` (Production)
- **Purpose**: Poll individual MT5 accounts for data
- **Data**: Account-specific information and positions
- **MT5 Usage**: Account login and data collection

### **Account Routes**
- **File**: `/backend/app/routes/mt5_terminal_routes.py`
- **Purpose**: API endpoints for account management
- **Functions**: Add/remove terminals, test connections, get account data
- **MT5 Usage**: Account management operations

### **Account Cache Functions**
- **File**: `/backend/app/services/cache_service.py` (lines 16-22)
- **Functions**: `set_account()`, `get_account()`
- **Purpose**: Cache account data with 30-second expiration
- **Usage**: Account widgets only

## Mini Chart Widget Dependencies

### **How Mini Charts Work**:
1. **Historical Data**: `/api/mt5/chart-history/{symbol}` provides chart line data
2. **Real-time Updates**: `/price/{symbol}` or WebSocket provides current price
3. **Chart Rendering**: JavaScript draws chart using historical + current data

### **Mini Chart Data Flow**:
```
symbols.txt → poller_market.py → cache_service.py → /price/{symbol} → Mini Chart Widget
             ↓
chart_collector.py → chart_history.db → /api/mt5/chart-history/{symbol} → Mini Chart Widget
```

### **Key Insight**: Mini charts have **ZERO dependency** on account data or terminal managers. They only use:
- Market price poller for current prices
- Chart collector for historical data
- Price cache for data access

## Critical Verification

### **MT5 Connection Analysis**:
- **Price System**: Uses single MT5 connection for market data only
- **Account System**: Uses multiple MT5 terminals with account credentials
- **Independence**: Price system works without any account terminals

### **Widget Testing Required**:
After removing account components, test these widgets to ensure they still work:
- Mini chart widgets (`/widgets/mini-chart`)
- Rotating asset widgets (`/widgets/rotating-asset`)
- Market ticker widgets (`/widgets/ticker`)
- Price-based widgets (anything showing current prices)

## Cleanup Safety Checklist

### **Before Removing Account Components**:
1. ✅ Verify mini charts work independently
2. ✅ Test price WebSocket functionality
3. ✅ Confirm chart history API works
4. ✅ Backup any existing account configurations

### **After Removing Account Components**:
1. Test all price-based widgets
2. Verify market data polling continues
3. Check chart history collection
4. Ensure price WebSocket streams work

## Migration Strategy

### **Phase 1: Remove Account Components**
- Safe to remove all account-related MT5 components
- Price data system remains fully functional
- Mini charts and price widgets unaffected

### **Phase 2: Implement New Authentication**
- Add user management system
- Create API-based account data collection
- Build new account widgets using 5ers API

### **Phase 3: Future Optimization**
- Consider moving price data to 5ers API as well
- Maintain current system as backup
- Gradual transition if needed

## Key Takeaway

The **price data system is completely independent** from account data. Mini charts, rotating charts, and all price-based widgets will continue working perfectly after removing account components. The MT5 price polling system requires no account credentials and operates separately from trader account management.

This analysis confirms it's safe to proceed with the cleanup plan.