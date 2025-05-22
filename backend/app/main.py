from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from fastapi.responses import JSONResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from app.services.cache_service import get_price
import asyncio
import os
import json

app = FastAPI()

static_path = os.path.join(os.path.dirname(__file__), "static")
app.mount("/static", StaticFiles(directory=static_path), name="static")

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

@app.post("/api/login-traders")
async def login_traders(request: Request):
    data = await request.json()
    # Expected: { "traders": [ { "label": ..., "login": ..., "password": ..., "server": ... }, ... ] }

    # TODO: Store credentials securely and launch terminals / polling
    return {"status": "received", "trader_count": len(data.get("traders", []))}


@app.post("/api/save-traders")
async def save_traders(request: Request):
    try:
        data = await request.json()
        traders = data.get("traders", [])

        # Build absolute path to .cache/logins.json
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        cache_dir = os.path.join(base_dir, ".cache")
        os.makedirs(cache_dir, exist_ok=True)
        login_file = os.path.join(cache_dir, "logins.json")

        # Save the trader data
        with open(login_file, "w") as f:
            json.dump({"traders": traders}, f, indent=2)

        return JSONResponse({"status": "success", "count": len(traders)})
    except Exception as e:
        return JSONResponse({"status": "error", "detail": str(e)}, status_code=500)