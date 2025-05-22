from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from app.services.cache_service import get_price
import asyncio
import os

app = FastAPI(title="WidgetForge API")

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

    # ✅ FIX: Use absolute path to symbols.txt to avoid broken file references
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
