from diskcache import Cache
import os

# Define cache location relative to project
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CACHE_DIR = os.path.abspath(os.path.join(BASE_DIR, "../../../.cache"))
cache = Cache(CACHE_DIR)

# 🔐 PRICE CACHE
def set_price(symbol: str, data: dict, expire: int = 10):
    cache.set(f"price:{symbol.upper()}", data, expire=expire)

def get_price(symbol: str):
    return cache.get(f"price:{symbol.upper()}")

# 👤 TRADER ACCOUNT CACHE
def set_account(account_id: str, data: dict, expire: int = 30):
    cache.set(f"account:{account_id}", data, expire=expire)

def get_account(account_id: str):
    return cache.get(f"account:{account_id}")

# 🧹 UTILS
def clear_all_cache():
    cache.clear()
