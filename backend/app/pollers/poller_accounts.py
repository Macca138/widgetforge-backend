import MetaTrader5 as mt5
import os
import json
import time

CACHE_DIR = os.path.join(os.path.dirname(__file__), "..", ".cache")
LOGIN_FILE = os.path.join(CACHE_DIR, "logins.json")

def save_json(path, data):
    with open(path, "w") as f:
        json.dump(data, f, indent=2)

def poll_trader(trader):
    login = trader["login"]
    password = trader["password"]
    server = trader["server"]
    terminal_path = trader["terminal_path"]
    label = trader["label"]

    # Initialize MT5 connection
    initialized = mt5.initialize(
        path=os.path.join(terminal_path, "terminal64.exe"),
        login=int(login),
        server=server,
        password=password
    )

    if not initialized:
        print(f"❌ Failed to initialize terminal for {label} ({login})")
        return

    # Get account info
    account_info = mt5.account_info()
    if account_info is None:
        print(f"⚠️ No account info for {label}")
        mt5.shutdown()
        return

    # Get open trade (first position only for now)
    positions = mt5.positions_get()
    trade_data = {}
    if positions:
        pos = positions[0]
        trade_data = {
            "symbol": pos.symbol,
            "direction": "BUY" if pos.type == mt5.ORDER_TYPE_BUY else "SELL",
            "entry": pos.price_open,
            "pl": pos.profit,
            "sl": pos.sl,
            "tp": pos.tp
        }

    data = {
        "label": label,
        "balance": account_info.balance,
        "equity": account_info.equity,
        **trade_data
    }

    # Save to cache file
    out_path = os.path.join(CACHE_DIR, f"trader_{login}.json")
    save_json(out_path, data)
    mt5.shutdown()
    print(f"✅ Updated trader: {label} ({login})")


def run_pollers():
    if not os.path.exists(LOGIN_FILE):
        print("❌ logins.json not found")
        return

    with open(LOGIN_FILE, "r") as f:
        config = json.load(f)

    while True:
        for trader in config.get("traders", []):
            try:
                poll_trader(trader)
            except Exception as e:
                print(f"❌ Error polling {trader.get('label')}:", str(e))
        time.sleep(1)

if __name__ == "__main__":
    run_pollers()

