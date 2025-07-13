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
    """Connect to MT5 with detailed error reporting"""
    mt5_path = "C:/MT5Terminals/Account1/terminal64.exe"
    
    print(f"🔍 Attempting MT5 connection: {mt5_path}")
    
    # Check if file exists first
    if not os.path.exists(mt5_path):
        print(f"❌ MT5 executable not found at: {mt5_path}")
        raise RuntimeError("❌ MT5 terminal64.exe not found")
    
    try:
        success = mt5.initialize(path=mt5_path)
        
        if success:
            terminal_info = mt5.terminal_info()
            account_info = mt5.account_info()
            print("✅ Connected to MT5")
            
            if terminal_info:
                print(f"   Terminal: {terminal_info.name}")
                print(f"   Build: {terminal_info.build}")
                print(f"   DLL Allowed: {terminal_info.dlls_allowed}")
                print(f"   Connected: {terminal_info.connected}")
            
            if account_info:
                print(f"   Account: {account_info.login} on {account_info.server}")
                print(f"   Trade Allowed: {account_info.trade_allowed}")
            else:
                print("   ⚠️ Not logged into trading account")
            
            return
        else:
            error_info = mt5.last_error()
            print(f"❌ MT5 Connection Failed!")
            print(f"   Error: {error_info}")
            print(f"💡 Common fixes:")
            print(f"   1. In MT5: Tools > Options > Expert Advisors > ✅ Allow DLL imports")
            print(f"   2. Restart MT5 terminal completely")
            print(f"   3. Run this script as Administrator")
            print(f"   4. Ensure account is logged in (not just terminal open)")
            
            # Try to get more details
            if terminal_info := mt5.terminal_info():
                if not terminal_info.dlls_allowed:
                    print(f"   ⚠️ DLL imports are DISABLED in MT5 settings!")
                if not terminal_info.connected:
                    print(f"   ⚠️ MT5 terminal is not connected to broker server!")
            
            raise RuntimeError("❌ MT5 initialization failed")
            
    except Exception as e:
        print(f"❌ Python Exception: {e}")
        raise RuntimeError(f"❌ MT5 initialization failed: {e}")


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
