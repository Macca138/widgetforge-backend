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
    """Connect to MT5 with multiple path attempts"""
    # Try multiple common MT5 paths
    mt5_paths = [
        "C:/MT5Terminals/Account1/terminal64.exe",  # Original custom path
        None,  # Auto-detect (default)
        "C:/Program Files/MetaTrader 5/terminal64.exe",  # Standard installation
        "C:/Program Files (x86)/MetaTrader 5/terminal64.exe",  # 32-bit system
    ]
    
    for i, path in enumerate(mt5_paths):
        try:
            if path is None:
                print("🔍 Attempting MT5 connection with auto-detect...")
                success = mt5.initialize()
            else:
                print(f"🔍 Attempting MT5 connection: {path}")
                success = mt5.initialize(path=path)
            
            if success:
                terminal_info = mt5.terminal_info()
                account_info = mt5.account_info()
                print("✅ Connected to MT5")
                if terminal_info:
                    print(f"   Terminal: {terminal_info.name}")
                    print(f"   Path: {terminal_info.path}")
                if account_info:
                    print(f"   Account: {account_info.login} on {account_info.server}")
                else:
                    print("   ⚠️ Not logged into trading account")
                return
        except Exception as e:
            print(f"   ❌ Failed with {path}: {e}")
            continue
    
    # If all attempts failed
    error_info = mt5.last_error()
    print("❌ All MT5 connection attempts failed!")
    print(f"   Last error: {error_info}")
    print("💡 Troubleshooting tips:")
    print("   1. Ensure MetaTrader 5 is running")
    print("   2. Check if terminal64.exe path is correct") 
    print("   3. Verify MT5 allows DLL imports (Tools > Options > Expert Advisors)")
    print("   4. Try running the diagnostic script: python diagnose_mt5.py")
    raise RuntimeError("❌ MT5 initialization failed after trying all paths")


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
