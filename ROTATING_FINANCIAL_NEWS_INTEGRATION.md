# Rotating Financial News Widget Integration

## Overview
Successfully integrated the rotating Financial Juice + Forex Factory widget into WidgetForge backend. This widget combines:

- **RSS News Feed**: Live Financial Juice news in chronological order
- **Economic Calendar**: Forex Factory high-impact events with actual results extracted from RSS
- **Rotating Display**: Auto-switches between news and calendar every 15 seconds
- **Stream Overlay Ready**: 300×500px transparent background for OBS/EVMUX

## Files Added

### 1. Services
- `backend/app/services/forex_factory_service.py` - Forex Factory calendar service with RSS result enhancement
- `backend/forex_factory_downloader.py` - Script to download weekly calendar data

### 2. Templates  
- `backend/app/templates/rotating_financial_news_widget.html` - Main widget template

### 3. Test Data
- `.cache/ff_calendar_test_20250711_161437.json` - Sample calendar data for testing

## API Endpoints Added

### Core APIs
- `GET /api/forex-factory/upcoming` - Get upcoming economic events
- `GET /api/forex-factory/high-impact` - Get high-impact events only  
- `GET /api/combined/rotation-data` - Combined data for rotating widget

### Widget Endpoint
- `GET /widgets/rotating-financial-news` - Main widget with customizable parameters

## Widget Features

### Visual Design
- ✅ **Transparent background** for stream overlay
- ✅ **Colored item cards** for readability
- ✅ **300×500px default size** (customizable)
- ✅ **Roboto font** with lighter weights
- ✅ **No scrollbars** (items fit perfectly)

### Data Integration
- ✅ **RSS chronological news** (Financial Juice)
- ✅ **Forex Factory high-impact events** only
- ✅ **Actual results extraction** from RSS news titles
- ✅ **Cross-referencing** CAD Employment Change → "83.1k", Unemployment Rate → "6.9%"

### Functionality
- ✅ **Auto-rotation** every 15 seconds
- ✅ **Manual switching** via dots
- ✅ **Live data updates** every 60 seconds
- ✅ **Error handling** and loading states

## Usage Examples

### Basic Widget
```html
<iframe src="http://5ers-stream.ddns.net:8000/widgets/rotating-financial-news" 
        width="300" height="500" frameborder="0"></iframe>
```

### Customized Widget
```html
<iframe src="http://5ers-stream.ddns.net:8000/widgets/rotating-financial-news?
        width=400&
        height=600&
        rotation_interval=20&
        title=Market Updates&
        font=Inter&
        bg_color=%23000000" 
        width="400" height="600" frameborder="0"></iframe>
```

## Deployment Steps

### 1. Update Calendar Data
Run the downloader to get current week's events:
```bash
cd backend
python forex_factory_downloader.py
```

### 2. Test Locally
```bash
cd backend  
uvicorn app.main:app --reload
```

Visit: `http://localhost:8000/widgets/rotating-financial-news`

### 3. Deploy to EVMUX
1. **Push to Git**: Commit all changes and push to repository
2. **Pull on VPS**: Git pull on Windows Server 2019 VPS
3. **Restart Service**: Restart WidgetForge backend service
4. **Test URL**: `http://5ers-stream.ddns.net:8000/widgets/rotating-financial-news`

## Integration with EVMUX

### OBS Stream Overlay
1. Add **Browser Source** in OBS
2. URL: `http://5ers-stream.ddns.net:8000/widgets/rotating-financial-news`
3. Width: `300`, Height: `500`
4. Custom CSS: (none needed - transparent background)

### Widget Parameters
- `width=300` - Widget width in pixels
- `height=500` - Widget height in pixels  
- `rotation_interval=15` - Seconds between rotations
- `news_count=8` - Number of news items to show
- `events_count=8` - Number of calendar events to show
- `title=Market News and Economic Events` - Widget title
- `font=Roboto` - Font family
- `auto_rotate=true` - Enable auto-rotation

## Maintenance

### Update Calendar Data
Run weekly to get fresh Forex Factory data:
```bash
python backend/forex_factory_downloader.py
```

### Monitor Performance
- RSS feeds cached for 5 minutes
- Calendar data cached for 1 hour  
- Widget refreshes data every 60 seconds

## Success Metrics

✅ **Perfect RSS Integration**: Financial Juice news in chronological order
✅ **Enhanced Calendar**: CAD Employment Change shows "83.1k", Unemployment Rate shows "6.9%"  
✅ **Stream Ready**: Transparent background, proper sizing, no scrollbars
✅ **Production Ready**: Integrated into main WidgetForge backend
✅ **EVMUX Compatible**: Ready for Windows Server deployment

The widget now seamlessly combines live financial news with economic calendar events, perfect for trading stream overlays!