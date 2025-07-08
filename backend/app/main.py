from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect, Header
from fastapi.responses import HTMLResponse
from fastapi.responses import JSONResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from app.services.cache_service import get_price, get_account
from app.routes.mt5_routes import router as mt5_router
from app.routes.mt5_terminal_routes import router as mt5_terminal_router
from dotenv import load_dotenv
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse
import asyncio
from pathlib import Path
import os
import json
import subprocess
import signal
import base64

load_dotenv("C:/WidgetForge/widgetforge-backend/.env")

AUTH_TOKEN = os.getenv("API_KEY")
print("🔑 AUTH_TOKEN loaded from .env:", AUTH_TOKEN)

class AdminAuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        path = request.url.path
        if path.startswith("/admin/") and path not in ["/admin/login", "/admin/dashboard"]:
            key = request.headers.get("X-API-KEY") or request.query_params.get("key")
            if key != AUTH_TOKEN:
                return JSONResponse({"detail": "Unauthorized"}, status_code=401)
        return await call_next(request)

app = FastAPI()
app.add_middleware(AdminAuthMiddleware)

# Include MT5 routes
app.include_router(mt5_router)
app.include_router(mt5_terminal_router)

@app.on_event("startup")
async def startup_event():
    """Load existing MT5 configuration on startup"""
    from app.services.mt5_manager import mt5_manager
    
    cache_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".cache"))
    config_file = os.path.join(cache_dir, "traders_config.json")
    
    if os.path.exists(config_file):
        try:
            with open(config_file, "r") as f:
                config = json.load(f)
            
            traders = config.get("traders", [])
            if traders:
                # Restore terminal configurations
                for trader in traders:
                    password = base64.b64decode(trader["password"]).decode()
                    mt5_manager.add_terminal(
                        login=trader["login"],
                        password=password,
                        server=trader["server"],
                        label=trader["label"],
                        terminal_path=trader["terminal_path"]
                    )
                
                # Start polling
                mt5_manager.start_polling(traders, interval=5)
                print(f"🚀 Restored {len(traders)} MT5 terminals and started polling")
        except Exception as e:
            print(f"⚠️ Failed to restore MT5 configuration: {e}")
    else:
        print("ℹ️ No existing MT5 configuration found")

static_path = os.path.join(os.path.dirname(__file__), "static")
app.mount("/static", StaticFiles(directory=static_path), name="static")

# ✅ Mount .cache as /static/data
cache_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".cache"))
app.mount("/static/data", StaticFiles(directory=cache_path), name="data")

templates = Jinja2Templates(directory="app/templates")


@app.get("/ping")
def ping():
    return {"status": "ok"}


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
    
@app.get("/admin/account-widget", response_class=HTMLResponse)
async def admin_account_widget(request: Request):
    return templates.TemplateResponse("admin_account_widget.html", {
        "request": request
    })

@app.get("/admin/mt5-manager", response_class=HTMLResponse)
async def admin_mt5_manager(request: Request):
    return templates.TemplateResponse("admin_mt5_manager.html", {
        "request": request
    })

@app.get("/admin/mt5-terminal-manager", response_class=HTMLResponse)
async def admin_mt5_terminal_manager(request: Request):
    return templates.TemplateResponse("admin_mt5_terminal_manager.html", {
        "request": request
    })

@app.get("/admin/enhanced-account-builder", response_class=HTMLResponse)
async def admin_enhanced_account_builder(request: Request):
    return templates.TemplateResponse("admin_enhanced_account_builder.html", {
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

@app.post("/api/save-traders")
async def save_traders(request: Request, x_api_key: str = Header(None)):
    if x_api_key != AUTH_TOKEN:
        return JSONResponse({"status": "unauthorized"}, status_code=401)

    try:
        data = await request.json()
        traders = data.get("traders", [])

        if len(traders) > 9:
            return JSONResponse({"status": "error", "detail": "Only 9 terminals are available."}, status_code=400)

        # Assign each trader to Account2 through Account10
        assigned = []
        for i, trader in enumerate(traders):
            trader["terminal_path"] = f"C:/MT5Terminals/Account{i + 2}"
    
        # Obfuscate password
            plain_pw = trader["password"]
            encoded_pw = base64.b64encode(plain_pw.encode()).decode()
            trader["password"] = encoded_pw

            assigned.append(trader)


        # Determine paths
        # Determine paths
        backend_dir = os.path.dirname(os.path.abspath(__file__))  # C:/WidgetForge/widgetforge-backend/backend
        base_dir = os.path.abspath(os.path.join(backend_dir, "..", ".."))  # C:/WidgetForge/widgetforge-backend
        cache_dir = os.path.join(base_dir, ".cache")
        login_file = os.path.join(cache_dir, "logins.json")
        pid_file = os.path.join(cache_dir, "poller.pid")
        poll_script = os.path.join(backend_dir, "app", "pollers", "poller_accounts.py")  # ✅ FIXED path

        # Save login file
        os.makedirs(cache_dir, exist_ok=True)
        with open(login_file, "w") as f:
            json.dump({"traders": assigned}, f, indent=2)

        # Kill previous poller (if any)
        if os.path.exists(pid_file):
            try:
                with open(pid_file, "r") as pf:
                    old_pid = int(pf.read())
                os.kill(old_pid, signal.SIGTERM)
                print(f"🛑 Killed old poller process: PID {old_pid}")
                os.remove(pid_file)
            except Exception as e:
                print(f"⚠️ Failed to kill old poller: {e}")

        # Start new poller
        try:
            process = subprocess.Popen(["python", poll_script])
            with open(pid_file, "w") as pf:
                pf.write(str(process.pid))
            print(f"🚀 Started new poller: PID {process.pid}")
        except Exception as e:
            return JSONResponse({"status": "error", "detail": f"Failed to start poller: {str(e)}"}, status_code=500)

        return JSONResponse({"status": "success", "count": len(assigned)})

    except Exception as e:
        return JSONResponse({"status": "error", "detail": str(e)}, status_code=500)
    

