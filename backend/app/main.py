from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from app.services.cache_service import get_price
import asyncio
import os

app = FastAPI()
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
    return templates.TemplateResponse("admin_ticker.html", {"request": request})

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
        "websocket_host": "62.171.135.138:8000"  # adjust if you're behind a domain/proxy later
    })
