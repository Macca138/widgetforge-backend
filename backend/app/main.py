from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect, Header
from fastapi.responses import HTMLResponse
from fastapi.responses import JSONResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from app.services.cache_service import get_price
from app.services.rss_service import rss_service
from app.services.forex_factory_service import forex_factory_service
from app.routes.mt5_routes import router as mt5_router
from app.routes.auth_routes import router as auth_router
from app.routes.account_routes import router as account_router
from app.routes.widget_routes import router as widget_router
from app.middleware.auth_middleware import AuthMiddleware
from app.services.fivers_api_client import initialize_api_client
from dotenv import load_dotenv
import asyncio
from pathlib import Path
import os
import json
import subprocess
import signal
import base64
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

load_dotenv("C:/WidgetForge/widgetforge-backend/.env")

app = FastAPI()
app.add_middleware(AuthMiddleware)

# Initialize 5ers API client if configured
fivers_api_key = os.getenv("FIVERS_API_KEY")
if fivers_api_key:
    fivers_api_url = os.getenv("FIVERS_API_URL", "https://api.the5ers.com/mt5/investor")
    initialize_api_client(fivers_api_key, fivers_api_url)
    logger.info("5ers API client initialized")
else:
    logger.info("5ers API client not configured (FIVERS_API_KEY not set)")

# Include routers
app.include_router(mt5_router)
app.include_router(auth_router)
app.include_router(account_router)
app.include_router(widget_router)


static_path = os.path.join(os.path.dirname(__file__), "static")
app.mount("/static", StaticFiles(directory=static_path), name="static")

# ✅ Mount .cache as /static/data
cache_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".cache"))
app.mount("/static/data", StaticFiles(directory=cache_path), name="data")

templates = Jinja2Templates(directory="app/templates")


@app.get("/ping")
def ping():
    return {"status": "ok"}

@app.get("/api/rss/financial-juice")
async def get_financial_juice_news(max_items: int = 20):
    """Get Financial Juice news from RSS feed"""
    try:
        news_items = rss_service.fetch_financial_juice_news(max_items)
        return {
            "success": True,
            "data": news_items,
            "count": len(news_items)
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "data": []
        }


@app.get("/price/{symbol}")
def get_price_data(symbol: str):
    data = get_price(symbol)
    if not data:
        return {"error": "Not found"}
    return data


@app.websocket("/ws/price-stream")
async def price_stream(websocket: WebSocket):
    await websocket.accept()
    print("📡 Client connected to /ws/price-stream")

    base_dir = os.path.dirname(os.path.abspath(__file__))
    symbols_file = os.path.join(base_dir, "pollers", "symbols.txt")

    try:
        with open(symbols_file, 'r') as f:
            symbols = [line.strip() for line in f if line.strip()]
    except FileNotFoundError:
        await websocket.close()
        print("❌ symbols.txt not found")
        return

    try:
        while True:
            payload = []
            for symbol in symbols:
                data = get_price(symbol)
                if data:
                    payload.append({
                        "symbol": symbol,
                        "price": data.get("price"),
                        "change_pct": data.get("change_pct"),
                        "spread": data.get("spread")
                    })
            await websocket.send_json(payload)
            await asyncio.sleep(1)
    except WebSocketDisconnect:
        print("❌ Client disconnected from /ws/price-stream")

@app.get("/admin/login", response_class=HTMLResponse)
async def admin_login(request: Request):
    return templates.TemplateResponse("admin_login.html", {"request": request})


@app.get("/admin/ticker", response_class=HTMLResponse)
async def admin_ticker(request: Request):
    base_dir = os.path.dirname(os.path.abspath(__file__))
    symbols_file = os.path.join(base_dir, "pollers", "symbols.txt")
    with open(symbols_file, 'r') as f:
        all_assets = [line.strip() for line in f if line.strip()]

    selected_assets = request.query_params.getlist("symbols")
    return templates.TemplateResponse("admin_ticker.html", {
        "request": request,
        "all_assets": all_assets,
        "selected_assets": selected_assets,
        "font": request.query_params.get("font", "Arial"),
        "font_size": request.query_params.get("fontSize", "16"),
        "font_color": request.query_params.get("fontColor", "#f6f6fd"),
        "bg_color": request.query_params.get("bgColor", "#000000"),
        "scroll_speed": request.query_params.get("scrollSpeed", "120"),
        "static_text": request.query_params.get("staticText", ""),
        "show_logo": request.query_params.get("show_logo", "false"),
        "asset_color": request.query_params.get("asset_color", "#ffffff"),
        "spread_color": request.query_params.get("spread_color", "#f6f6fd"),
        "up_color": request.query_params.get("up_color", "#00ff00"),
        "down_color": request.query_params.get("down_color", "#ff4444"),
    })

@app.get("/admin/enhanced-ticker", response_class=HTMLResponse)
async def admin_enhanced_ticker(request: Request):
    base_dir = os.path.dirname(os.path.abspath(__file__))
    symbols_file = os.path.join(base_dir, "pollers", "symbols.txt")
    with open(symbols_file, 'r') as f:
        all_assets = [line.strip() for line in f if line.strip()]
    
    return templates.TemplateResponse("admin_enhanced_ticker.html", {
        "request": request,
        "all_assets": all_assets
    })

@app.get("/admin/dashboard", response_class=HTMLResponse)
async def admin_dashboard(request: Request):
    return templates.TemplateResponse("admin_dashboard.html", {
        "request": request
    })

@app.get("/widgets/ticker", response_class=HTMLResponse)
async def widget_ticker(request: Request):
    params = request.query_params
    return templates.TemplateResponse("ticker_widget.html", {
        "request": request,
        "symbols": params.get("symbols", ""),
        "font": params.get("font", "Arial"),
        "font_size": params.get("fontSize", "16"),
        "font_color": params.get("fontColor", "#ffffff"),
        "bg_color": params.get("bgColor", "#000000"),
        "scroll_speed": int(params.get("scrollSpeed", "30")) / 10,  # convert ms to seconds
        "static_text": params.get("staticText", ""),
        "show_logo": params.get("show_logo", "false"),
        "asset_color": params.get("asset_color", "#ffffff"),
        "spread_color": params.get("spread_color", "#cccccc"),
        "up_color": params.get("up_color", "#00ff00"),
        "down_color": params.get("down_color", "#ff4444"),
        "websocket_host": "62.171.135.138:8000"
    })

@app.get("/widgets/enhanced-ticker", response_class=HTMLResponse)
async def enhanced_ticker_widget(request: Request):
    params = request.query_params
    return templates.TemplateResponse("enhanced_ticker_widget.html", {
        "request": request,
        # Data Configuration
        "symbols": params.get("symbols", ""),
        "static_text": params.get("staticText", ""),
        "websocket_host": request.headers.get("host", "62.171.135.138:8000"),
        
        # Display Mode
        "display_mode": params.get("display_mode", "scroll"),  # scroll, static, grid, card, compact
        "update_animation": params.get("update_animation", "none"),  # none, fade, slide
        
        # Typography
        "font": params.get("font", "Inter"),
        "font_size": params.get("fontSize", "16"),
        "font_weight": params.get("fontWeight", "400"),
        "font_color": params.get("fontColor", "#ffffff"),
        
        # Colors
        "bg_color": params.get("bgColor", "#000000"),
        "bg_gradient": params.get("bgGradient", ""),
        "asset_color": params.get("assetColor", "#ffffff"),
        "asset_font_weight": params.get("assetFontWeight", "600"),
        "asset_font_size": params.get("assetFontSize", "100"),
        "price_font_weight": params.get("priceFontWeight", "500"),
        "up_color": params.get("upColor", "#00ff88"),
        "down_color": params.get("downColor", "#ff4444"),
        "neutral_color": params.get("neutralColor", "#cccccc"),
        "spread_color": params.get("spreadColor", "#999999"),
        "spread_opacity": params.get("spreadOpacity", "0.8"),
        "spread_font_size": params.get("spreadFontSize", "85"),
        "change_font_size": params.get("changeFontSize", "90"),
        
        # Layout
        "padding": params.get("padding", "0"),
        "item_spacing": params.get("itemSpacing", "20"),
        "item_margin": params.get("itemMargin", "30"),
        "item_gap": params.get("itemGap", "8"),
        "item_layout": params.get("itemLayout", "row"),  # row, column
        "item_align": params.get("itemAlign", "center"),
        
        # Scroll Mode
        "scroll_speed": params.get("scrollSpeed", "30"),
        
        # Static Mode
        "static_align": params.get("staticAlign", "center"),  # left, center, right
        
        # Grid Mode
        "grid_columns": params.get("gridColumns", "3"),
        "grid_gap": params.get("gridGap", "20"),
        "grid_padding": params.get("gridPadding", "20"),
        
        # Card Mode
        "card_gap": params.get("cardGap", "15"),
        "card_padding": params.get("cardPadding", "20"),
        "card_bg_color": params.get("cardBgColor", "rgba(255,255,255,0.05)"),
        "card_border_width": params.get("cardBorderWidth", "1"),
        "card_border_color": params.get("cardBorderColor", "rgba(255,255,255,0.1)"),
        "card_border_radius": params.get("cardBorderRadius", "8"),
        "card_inner_padding": params.get("cardInnerPadding", "15"),
        "card_shadow": params.get("cardShadow", "0 2px 8px rgba(0,0,0,0.1)"),
        "card_hover_shadow": params.get("cardHoverShadow", "0 4px 16px rgba(0,0,0,0.2)"),
        
        # Features
        "show_spread": params.get("showSpread", "true"),
        "show_timestamp": params.get("showTimestamp", "false"),
        "timestamp_format": params.get("timestampFormat", "time"),  # time, short, full
        "timestamp_color": params.get("timestampColor", "#666666"),
        "timestamp_font_size": params.get("timestampFontSize", "80"),
        "timestamp_opacity": params.get("timestampOpacity", "0.7"),
        "show_connection_status": params.get("showConnectionStatus", "false"),
        "price_decimals": params.get("priceDecimals", "5"),
        
        # Logo
        "show_logo": params.get("showLogo", "false"),
        "logo_url": params.get("logoUrl", ""),
        "logo_position": params.get("logoPosition", "top"),  # top, bottom
        "logo_height": params.get("logoHeight", "30"),
        "logo_margin": params.get("logoMargin", "10px"),
        
        # Custom CSS
        "custom_css": params.get("customCSS", "")
    })

@app.get("/widgets/test-simple", response_class=HTMLResponse)
async def test_simple_widget(request: Request):
    params = request.query_params
    return templates.TemplateResponse("test_simple.html", {
        "request": request,
        "font_size": params.get("fontSize", "16"),
        "symbols": params.get("symbols", ""),
        "show_spread": params.get("showSpread", "true")
    })

@app.get("/widgets/smooth-ticker", response_class=HTMLResponse)
async def smooth_ticker_widget(request: Request):
    params = request.query_params
    return templates.TemplateResponse("smooth_ticker_widget.html", {
        "request": request,
        # Data Configuration
        "symbols": params.get("symbols", ""),
        "static_text": params.get("staticText", ""),
        "websocket_host": "5ers-stream.ddns.net" if "5ers-stream.ddns.net" in request.headers.get("host", "") else "127.0.0.1:8000",
        "websocket_protocol": "wss" if "5ers-stream.ddns.net" in request.headers.get("host", "") else "ws",
        
        # Typography
        "font": params.get("font", "Inter"),
        "font_size": params.get("fontSize", "16"),
        "font_weight": params.get("fontWeight", "400"),
        "font_color": params.get("fontColor", "#ffffff"),
        
        # Colors
        "bg_color": params.get("bgColor", "#000000"),
        "bg_gradient": params.get("bgGradient", ""),
        "asset_color": params.get("assetColor", "#ffffff"),
        "up_color": params.get("upColor", "#00ff88"),
        "down_color": params.get("downColor", "#ff4444"),
        "neutral_color": params.get("neutralColor", "#cccccc"),
        "spread_color": params.get("spreadColor", "#999999"),
        
        # Animation
        "scroll_speed": params.get("scrollSpeed", "30"),
        
        # Features
        "show_spread": params.get("showSpread", "true"),
        "show_connection_status": params.get("showConnectionStatus", "false"),
        
        # Logo
        "show_logo": params.get("showLogo", "false"),
        "logo_url": params.get("logoUrl", ""),
        "logo_height": params.get("logoHeight", "30")
    })

@app.get("/widgets/canvas-ticker", response_class=HTMLResponse)
async def canvas_ticker_widget(request: Request):
    params = request.query_params
    return templates.TemplateResponse("canvas_ticker_widget.html", {
        "request": request,
        # Data Configuration
        "symbols": params.get("symbols", ""),
        "static_text": params.get("staticText", ""),
        "websocket_host": request.headers.get("host", "62.171.135.138:8000"),
        
        # Typography
        "font": params.get("font", "Inter"),
        "font_size": params.get("fontSize", "16"),
        "font_weight": params.get("fontWeight", "400"),
        "font_color": params.get("fontColor", "#ffffff"),
        
        # Colors
        "bg_color": params.get("bgColor", "#000000"),
        "bg_gradient": params.get("bgGradient", ""),
        "asset_color": params.get("assetColor", "#ffffff"),
        "up_color": params.get("upColor", "#00ff88"),
        "down_color": params.get("downColor", "#ff4444"),
        "neutral_color": params.get("neutralColor", "#cccccc"),
        "spread_color": params.get("spreadColor", "#999999"),
        
        # Animation
        "scroll_speed": params.get("scrollSpeed", "30"),
        
        # Features
        "show_spread": params.get("showSpread", "true"),
        "show_connection_status": params.get("showConnectionStatus", "false"),
        
        # Logo
        "show_logo": params.get("showLogo", "false"),
        "logo_url": params.get("logoUrl", ""),
        "logo_height": params.get("logoHeight", "30")
    })

@app.get("/widgets/market-sessions", response_class=HTMLResponse)
async def market_sessions_widget(request: Request):
    params = dict(request.query_params)
    
    # Handle background opacity
    bg_opacity = params.get("bgOpacity", "")
    if bg_opacity:
        bg_opacity = f"{int(float(bg_opacity) * 255):02x}"  # Convert 0-1 to hex
    
    return templates.TemplateResponse("market_sessions_widget.html", {
        "request": request,
        "font": params.get("font", "Inter"),
        "font_size": params.get("fontSize", "16"),
        "font_weight": params.get("fontWeight", "700"),
        "font_color": params.get("fontColor", "#fff"),
        "bg_color": params.get("bgColor", "#000000"),
        "bg_opacity": bg_opacity,
        "border_radius": params.get("borderRadius", "0"),
        "session_color": params.get("sessionColor", "#DDFD6C"),
        "clock_color": params.get("clockColor", "#DDFD6C"),
    })

@app.get("/widgets/mini-chart", response_class=HTMLResponse)
async def mini_chart_widget(request: Request):
    params = dict(request.query_params)
    
    return templates.TemplateResponse("mini_chart_widget.html", {
        "request": request,
        # Chart configuration
        "symbol": params.get("symbol", "EURUSD"),
        "hours": params.get("hours", "24"),
        "max_points": params.get("maxPoints", "180"),
        "update_interval": params.get("updateInterval", "180"),
        
        # Dimensions
        "width": params.get("width", "300"),
        "height": params.get("height", "150"),
        "border_radius": params.get("borderRadius", "8"),
        
        # Colors
        "bg_color": params.get("bgColor", "rgba(0, 0, 0, 0.8)"),
        "text_color": params.get("textColor", "#ffffff"),
        "line_color": params.get("lineColor", "#00ff88"),
        "fill_color": params.get("fillColor", "#00ff88"),
        "up_color": params.get("upColor", "#00ff88"),
        "down_color": params.get("downColor", "#ff4444"),
        "neutral_color": params.get("neutralColor", "#cccccc"),
        "grid_color": params.get("gridColor", "rgba(255, 255, 255, 0.1)"),
        
        # Features
        "show_grid": params.get("showGrid", "true"),
    })

@app.get("/widgets/rotating-asset", response_class=HTMLResponse)
async def rotating_asset_widget(request: Request):
    params = dict(request.query_params)
    
    return templates.TemplateResponse("rotating_asset_widget.html", {
        "request": request,
        
        # Layout
        "width": params.get("width", "300"),
        "height": params.get("height", "400"),
        "border_radius": params.get("borderRadius", "8"),
        
        # Typography
        "font": params.get("font", "Inter"),
        "font_size": params.get("fontSize", "14"),
        "font_weight": params.get("fontWeight", "600"),
        
        # Colors
        "bg_color": params.get("bgColor", "rgba(0, 0, 0, 0.9)"),
        "text_color": params.get("textColor", "#ffffff"),
        "chart_color": params.get("chartColor", "#00ff88"),
        "up_color": params.get("upColor", "#00ff88"),
        "down_color": params.get("downColor", "#ff4444"),
        "neutral_color": params.get("neutralColor", "#cccccc"),
        "spread_color": params.get("spreadColor", "#00ffff"),
    })

@app.get("/widgets/rotating-asset-test", response_class=HTMLResponse)
async def rotating_asset_test_widget(request: Request):
    return templates.TemplateResponse("rotating_asset_test.html", {
        "request": request
    })

@app.get("/widgets/rotating-asset-debug", response_class=HTMLResponse)
async def rotating_asset_debug_widget(request: Request):
    return templates.TemplateResponse("rotating_asset_debug.html", {
        "request": request
    })

@app.get("/widgets/rotating-asset-minimal", response_class=HTMLResponse)
async def rotating_asset_minimal_widget(request: Request):
    return templates.TemplateResponse("rotating_asset_minimal.html", {
        "request": request
    })

@app.get("/assets", response_class=HTMLResponse)
async def get_assets():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    symbols_file = os.path.join(base_dir, "pollers", "symbols.txt")

    try:
        with open(symbols_file, "r") as f:
            symbols = [line.strip() for line in f if line.strip()]
        return "<option>" + "</option><option>".join(symbols) + "</option>"
    except Exception as e:
        return f"<option disabled>Error loading symbols</option>"
    

@app.get("/admin/enhanced-account-builder", response_class=HTMLResponse)
async def admin_enhanced_account_builder(request: Request):
    return templates.TemplateResponse("admin_enhanced_account_builder.html", {
        "request": request
    })

@app.get("/admin/account-manager", response_class=HTMLResponse)
async def admin_account_manager(request: Request):
    return templates.TemplateResponse("admin_account_manager.html", {
        "request": request
    })

@app.get("/admin/mini-chart-builder", response_class=HTMLResponse)
async def admin_mini_chart_builder(request: Request):
    return templates.TemplateResponse("admin_mini_chart.html", {
        "request": request
    })

@app.get("/widgets/account-widget", response_class=HTMLResponse)
async def account_widget(request: Request):
    params = request.query_params

    return templates.TemplateResponse("account_widget.html", {
        "request": request,
        "layout": params.get("layout", "horizontal"),
        "fields": params.get("fields", "name,balance,equity").split(","),
        "font": params.get("font", "Inter"),
        "font_size": params.get("fontSize", "16"),
        "font_color": params.get("fontColor", "#ffffff"),
        "bg_color": params.get("bgColor", "#000000"),
        "traders": params.get("traders", "[]")
    })

@app.get("/widgets/enhanced-account-widget", response_class=HTMLResponse)
async def enhanced_account_widget(request: Request):
    params = request.query_params
    
    # Parse terminal IDs
    terminal_ids_str = params.get("terminal_ids", "")
    terminal_ids = [int(tid.strip()) for tid in terminal_ids_str.split(",") if tid.strip().isdigit()]

    return templates.TemplateResponse("enhanced_account_widget.html", {
        "request": request,
        "layout": params.get("layout", "grid"),
        "fields": params.get("fields", "balance,equity,profit").split(","),
        "font": params.get("font", "Inter"),
        "font_size": params.get("fontSize", "16"),
        "font_color": params.get("fontColor", "#ffffff"),
        "bg_color": params.get("bgColor", "#000000"),
        "terminal_ids": terminal_ids,
        "sort_by": params.get("sort_by", "profit"),
        "max_traders": int(params.get("max_traders", "10")),
        "scroll_speed": int(params.get("scroll_speed", "30")),
        "trader_name_color": params.get("trader_name_color", "#00ff88"),
        "balance_color": params.get("balance_color", "#ffffff"),
        "equity_color": params.get("equity_color", "#ffffff"),
        "profit_positive_color": params.get("profit_positive_color", "#00ff88"),
        "profit_negative_color": params.get("profit_negative_color", "#ff4444"),
        "profit_neutral_color": params.get("profit_neutral_color", "#cccccc"),
        "label_color": params.get("label_color", "#cccccc")
    })

@app.get("/widgets/financial-juice", response_class=HTMLResponse)
async def financial_juice_widget(request: Request):
    """Financial Juice RSS news widget with customizable styling"""
    params = request.query_params
    
    return templates.TemplateResponse("financial_juice_widget.html", {
        "request": request,
        # Widget configuration
        "title": params.get("title", "Financial Juice News"),
        "max_items": int(params.get("max_items", "20")),
        "refresh_interval": int(params.get("refresh_interval", "60")),
        
        # Layout and sizing
        "width": params.get("width", "100%"),
        "height": params.get("height", "400"),
        "padding": params.get("padding", "10"),
        "item_spacing": params.get("item_spacing", "8"),
        "item_padding": params.get("item_padding", "12"),
        "border_radius": params.get("border_radius", "6"),
        
        # Typography
        "font": params.get("font", "Inter"),
        "font_size": params.get("font_size", "14"),
        "title_font_size": params.get("title_font_size", "18"),
        "news_title_size": params.get("news_title_size", "14"),
        "meta_font_size": params.get("meta_font_size", "11"),
        "badge_font_size": params.get("badge_font_size", "10"),
        "small_font_size": params.get("small_font_size", "12"),
        "title_weight": params.get("title_weight", "600"),
        
        # Colors
        "bg_color": params.get("bg_color", "#1e222d"),
        "font_color": params.get("font_color", "#b2b5be"),
        "title_color": params.get("title_color", "#ffffff"),
        "secondary_color": params.get("secondary_color", "#888"),
        "accent_color": params.get("accent_color", "#4a5568"),
        "item_bg_color": params.get("item_bg_color", "#2d3748"),
        "hover_color": params.get("hover_color", "#374151"),
        "normal_color": params.get("normal_color", "#4a90e2"),
        "high_impact_color": params.get("high_impact_color", "#e53e3e"),
        "high_impact_bg": params.get("high_impact_bg", "#4a1f1f"),
        "high_impact_text_color": params.get("high_impact_text_color", "#ff6b6b"),
        "news_title_color": params.get("news_title_color", "#ffffff"),
        "meta_color": params.get("meta_color", "#999"),
        "error_color": params.get("error_color", "#e53e3e"),
        
        # Behavior
        "show_high_impact_badge": params.get("show_high_impact_badge", "true"),
        "open_links_new_tab": params.get("open_links_new_tab", "true"),
        "animate_new_items": params.get("animate_new_items", "true")
    })

@app.get("/api/forex-factory/upcoming")
async def get_upcoming_events(max_items: int = 20, impact: str = None):
    """Get upcoming Forex Factory economic calendar events"""
    try:
        events = forex_factory_service.get_upcoming_events(max_items, impact)
        return {
            "success": True,
            "data": events,
            "count": len(events)
        }
    except Exception as e:
        logger.error(f"Error in Forex Factory API endpoint: {e}")
        return {
            "success": False,
            "error": str(e),
            "data": []
        }

@app.get("/api/forex-factory/high-impact")
async def get_high_impact_events(max_items: int = 10):
    """Get upcoming high-impact Forex Factory events"""
    try:
        events = forex_factory_service.get_high_impact_events(max_items)
        return {
            "success": True,
            "data": events,
            "count": len(events)
        }
    except Exception as e:
        logger.error(f"Error in high-impact events API endpoint: {e}")
        return {
            "success": False,
            "error": str(e),
            "data": []
        }

@app.get("/api/combined/rotation-data")
async def get_rotation_data(news_count: int = 8, events_count: int = 8):
    """Get data for rotating widget display with cross-referenced news"""
    try:
        # Get news data (fetch more to find relevant items, then limit display)
        all_news_items = rss_service.fetch_financial_juice_news(50)
        news_items = all_news_items[:news_count]
        
        # Get ONLY Forex Factory high-impact events (past and upcoming)
        recent_past_events = forex_factory_service.get_recent_past_events(events_count, "High") 
        upcoming_events = forex_factory_service.get_upcoming_events(events_count, "High")
        
        # Enhance events with actual results from RSS news
        enhanced_past_events = forex_factory_service.enhance_events_with_rss_results(recent_past_events, all_news_items)
        enhanced_upcoming_events = forex_factory_service.enhance_events_with_rss_results(upcoming_events, all_news_items)
        
        # Combine events with priority for upcoming events (ensure USD PPI and other future events show)
        # Prioritize upcoming events, then fill remaining slots with past events
        max_upcoming = max(6, events_count // 2)  # Ensure at least 6 upcoming events or half the total
        max_past = events_count - len(enhanced_upcoming_events[:max_upcoming])
        
        calendar_display_events = enhanced_upcoming_events[:max_upcoming] + enhanced_past_events[:max_past]
        
        # Sort combined events by timestamp for proper chronological order
        calendar_display_events.sort(key=lambda x: x.get('timestamp', 0))
        all_events = forex_factory_service.get_todays_events() + upcoming_events
        
        # Cross-reference news with calendar events (but keep chronological order)
        enhanced_news = rss_service.cross_reference_with_calendar(news_items, all_events)
        
        # Get pinned items (but disable pinned event to avoid duplicates)
        pinned_news = rss_service.get_recent_high_impact_news()
        pinned_event = None  # Disable pinned event since we show recent events in main list
        
        return {
            "success": True,
            "data": {
                "news_feed": {
                    "items": enhanced_news,
                    "pinned": pinned_news
                },
                "calendar_feed": {
                    "items": calendar_display_events,
                    "pinned": pinned_event
                },
                "rotation_ready": True,
                "last_updated": datetime.now().isoformat()
            }
        }
    except Exception as e:
        logger.error(f"Error in rotation data API endpoint: {e}")
        return {
            "success": False,
            "error": str(e),
            "data": {}
        }

@app.get("/widgets/rotating-financial-news", response_class=HTMLResponse)
async def rotating_financial_news_widget(request: Request):
    """Rotating widget combining Financial Juice news and Forex Factory calendar"""
    params = request.query_params
    
    return templates.TemplateResponse("rotating_financial_news_widget.html", {
        "request": request,
        # Widget configuration
        "title": params.get("title", "Market & Economic News"),
        "rotation_interval": int(params.get("rotation_interval", "10")),
        "refresh_interval": int(params.get("refresh_interval", "60")),
        "auto_rotate": params.get("auto_rotate", "true").lower(),
        "news_count": int(params.get("news_count", "8")),
        "events_count": int(params.get("events_count", "8")),
        
        # Layout and sizing
        "width": params.get("width", "300"),
        "height": params.get("height", "500"),
        "padding": params.get("padding", "16"),
        "item_spacing": params.get("item_spacing", "8"),
        "item_padding": params.get("item_padding", "12"),
        "border_radius": params.get("border_radius", "8"),
        
        # Typography
        "font": params.get("font", "Roboto"),
        "font_size": params.get("font_size", "14"),
        "title_font_size": params.get("title_font_size", "18"),
        "news_title_size": params.get("news_title_size", "14"),
        "meta_font_size": params.get("meta_font_size", "11"),
        "badge_font_size": params.get("badge_font_size", "9"),
        "small_font_size": params.get("small_font_size", "12"),
        "title_weight": params.get("title_weight", "600"),
        
        # Colors
        "bg_color": params.get("bg_color", "#1a1d29"),
        "font_color": params.get("font_color", "#e2e8f0"),
        "title_color": params.get("title_color", "#ffffff"),
        "secondary_color": params.get("secondary_color", "#64748b"),
        "accent_color": params.get("accent_color", "#3b82f6"),
        "item_bg_color": params.get("item_bg_color", "#2d3748"),
        "hover_color": params.get("hover_color", "#374151"),
        "normal_color": params.get("normal_color", "#60a5fa"),
        "high_impact_color": params.get("high_impact_color", "#ef4444"),
        "high_impact_bg": params.get("high_impact_bg", "#3c1e1e"),
        "high_impact_text_color": params.get("high_impact_text_color", "#fca5a5"),
        "news_title_color": params.get("news_title_color", "#f8fafc"),
        "meta_color": params.get("meta_color", "#94a3b8"),
        "error_color": params.get("error_color", "#ef4444"),
        
        # Behavior
        "open_links_new_tab": params.get("open_links_new_tab", "true")
    })

    

