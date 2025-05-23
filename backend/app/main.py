from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect, Header
from fastapi.responses import HTMLResponse
from fastapi.responses import JSONResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from app.services.cache_service import get_price
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
        "font_color": request.query_params.get("fontColor", "#ffffff"),
        "bg_color": request.query_params.get("bgColor", "#000000"),
        "scroll_speed": request.query_params.get("scrollSpeed", "30"),
        "static_text": request.query_params.get("staticText", ""),
        "show_logo": request.query_params.get("show_logo", "false"),
        "asset_color": request.query_params.get("asset_color", "#ffffff"),
        "spread_color": request.query_params.get("spread_color", "#cccccc"),
        "up_color": request.query_params.get("up_color", "#00ff00"),
        "down_color": request.query_params.get("down_color", "#ff4444"),
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
    

