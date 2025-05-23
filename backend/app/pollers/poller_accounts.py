
import MetaTrader5 as mt5
import os
import json
import time
import base64
import shutil
import subprocess

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
CACHE_DIR = os.path.join(BASE_DIR, ".cache")
LOGIN_FILE = os.path.join(CACHE_DIR, "logins.json")

def save_json(path, data):
    with open(path, "w") as f:
        json.dump(data, f, indent=2)

def poll_trader(trader):
    login = trader["login"]
    password = base64.b64decode(trader["password"]).decode()
    server = trader["server"]
    terminal_path = trader["terminal_path"]
    label = trader["label"]

    # Step 1: Clean config & logs
    for subdir in ["config", "logs"]:
        dir_path = os.path.join(terminal_path, subdir)
        if os.path.exists(dir_path):
            shutil.rmtree(dir_path)

    # Step 2: Launch MT5 terminal
    exe_path = os.path.join(terminal_path, "terminal64.exe")
    subprocess.Popen([exe_path])
    time.sleep(10)  # wait for MT5 to start up

    # Step 3: Initialize and Login
    initialized = mt5.initialize(
        path=exe_path
    )

    if not initialized:
        print(f"❌ Failed to initialize terminal for {label} ({login}):", mt5.last_error())
        return

    if not mt5.login(int(login), password=password, server=server):
        print(f"❌ Login failed for {label} ({login}):", mt5.last_error())
        mt5.shutdown()
        return

    # Step 4: Get account info
    account_info = mt5.account_info()
    if account_info is None:
        print(f"⚠️ No account info for {label}")
        mt5.shutdown()
        return

    # Step 5: Get open trade (first position only for now)
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

    # Step 6: Save to cache file
    out_path = os.path.join(CACHE_DIR, f"trader_{login}.json")
    save_json(out_path, data)
    mt5.shutdown()
    print(f"✅ Updated trader: {label} ({login})")

def run_pollers():
    if not os.path.exists(LOGIN_FILE):
        print(f"❌ logins.json not found at {LOGIN_FILE}")
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
