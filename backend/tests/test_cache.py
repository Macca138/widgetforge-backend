from backend.app.services.cache_service import (
    set_price, get_price, set_account, get_account, clear_all_cache
)

def test_cache_system():
    # Clear everything first
    clear_all_cache()

    # Test price caching
    price_data = {"symbol": "EURUSD", "bid": 1.0865, "ask": 1.0868}
    set_price("EURUSD", price_data)
    cached_price = get_price("EURUSD")
    assert cached_price == price_data, "Price cache failed"
    print("✅ Price cache passed")

    # Test trader account caching
    account_data = {"account_id": "trader001", "balance": 10000, "equity": 10500}
    set_account("trader001", account_data)
    cached_account = get_account("trader001")
    assert cached_account == account_data, "Account cache failed"
    print("✅ Account cache passed")

if __name__ == "__main__":
    test_cache_system()
