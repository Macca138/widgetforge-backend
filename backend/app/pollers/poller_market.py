import MetaTrader5 as mt5
import time
import os
import sys
from datetime import datetime, timedelta
import pytz

# Add backend directory to Python path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

from app.services.cache_service import set_price


def connect_mt5():
    if not mt5.initialize(path="C:/MT5Terminals/Account1/terminal64.exe"):
        raise RuntimeError("❌ MT5 initialization failed")
    print("✅ Connected to MT5")


def get_previous_close(symbol):
    # Get previous day's daily candle close
    now = datetime.now(pytz.utc)
    midnight = datetime(now.year, now.month, now.day, tzinfo=pytz.utc)
    yesterday = midnight - timedelta(days=1)

    candles = mt5.copy_rates_from(symbol, mt5.TIMEFRAME_D1, yesterday, 1)
    if candles is None or len(candles) == 0:
        return None
    return candles[0]['close']


def fetch_price(symbol):
    tick = mt5.symbol_info_tick(symbol)
    if tick is None:
        raise ValueError(f"⚠️ Symbol {symbol} not found or not available")

    bid = tick.bid
    ask = tick.ask
    price = (bid + ask) / 2
    spread = round(ask - bid, 5)

    last_close = get_previous_close(symbol)
    if last_close is None:
        raise ValueError(f"⚠️ Could not retrieve previous close for {symbol}")

    change = round(price - last_close, 5)
    change_pct = round((change / last_close) * 100, 2)

    return {
        "symbol": symbol,
        "price": round(price, 5),
        "change_pct": change_pct,
        "spread": spread,
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
    }


def run_mt5_poll():
    connect_mt5()
    
    # Get the correct path to symbols.txt
    script_dir = os.path.dirname(os.path.abspath(__file__))
    symbols_file = os.path.join(script_dir, 'symbols.txt')
    
    with open(symbols_file, 'r') as f:
        symbols = [line.strip() for line in f if line.strip()]

    while True:
        for symbol in symbols:
            try:
                data = fetch_price(symbol)
                set_price(symbol, data)
                print(f"✅ {symbol}: {data['price']} ({data['change_pct']}%) Spread: {data['spread']}")
            except Exception as e:
                print(f"❌ Error with {symbol}: {e}")
        time.sleep(1)  # Adjust as needed

if __name__ == "__main__":
    run_mt5_poll()
