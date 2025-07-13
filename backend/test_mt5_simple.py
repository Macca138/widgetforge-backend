#!/usr/bin/env python3
"""
Simple MT5 Connection Test
Quick test for the exact path you specified
"""

import MetaTrader5 as mt5
import os

def test_specific_path():
    """Test the exact MT5 path you specified"""
    mt5_path = "C:/MT5Terminals/Account1/terminal64.exe"
    
    print("=" * 50)
    print("MT5 CONNECTION TEST - SPECIFIC PATH")
    print("=" * 50)
    
    # Check if file exists
    print(f"🔍 Checking path: {mt5_path}")
    if os.path.exists(mt5_path):
        print("✅ File exists")
    else:
        print("❌ File not found")
        return False
    
    # Test connection
    print(f"\n🔌 Testing MT5 connection...")
    try:
        success = mt5.initialize(path=mt5_path)
        
        if success:
            print("✅ MT5 Connection Successful!")
            
            # Get detailed info
            terminal_info = mt5.terminal_info()
            account_info = mt5.account_info()
            
            print(f"\n📊 Terminal Information:")
            if terminal_info:
                print(f"   Name: {terminal_info.name}")
                print(f"   Company: {terminal_info.company}")
                print(f"   Path: {terminal_info.path}")
                print(f"   Build: {terminal_info.build}")
                print(f"   Connected: {terminal_info.connected}")
                print(f"   DLL Allowed: {terminal_info.dlls_allowed}")
                print(f"   Trade Allowed: {terminal_info.trade_allowed}")
            
            print(f"\n👤 Account Information:")
            if account_info:
                print(f"   Login: {account_info.login}")
                print(f"   Server: {account_info.server}")
                print(f"   Name: {account_info.name}")
                print(f"   Company: {account_info.company}")
                print(f"   Currency: {account_info.currency}")
                print(f"   Balance: ${account_info.balance}")
                print(f"   Trade Allowed: {account_info.trade_allowed}")
            else:
                print("   ⚠️ No account logged in")
            
            # Test symbol access
            print(f"\n📈 Symbol Test:")
            symbols = mt5.symbols_get()
            if symbols:
                print(f"   Available symbols: {len(symbols)}")
                print(f"   First few symbols: {[s.name for s in symbols[:5]]}")
            else:
                print("   ❌ No symbols available")
            
            # Test a simple symbol
            test_symbol = "EURUSD"
            tick = mt5.symbol_info_tick(test_symbol)
            if tick:
                print(f"   {test_symbol} current price: Bid={tick.bid}, Ask={tick.ask}")
            else:
                print(f"   ❌ Could not get {test_symbol} price")
            
            mt5.shutdown()
            return True
            
        else:
            error = mt5.last_error()
            print(f"❌ MT5 Connection Failed!")
            print(f"   Error Code: {error[0] if error else 'Unknown'}")
            print(f"   Error Message: {error[1] if error and len(error) > 1 else 'No details'}")
            
            print(f"\n💡 Common Solutions:")
            print(f"   1. Check MT5 is running and logged in")
            print(f"   2. Enable DLL imports: Tools > Options > Expert Advisors > Allow DLL imports")
            print(f"   3. Run Python as Administrator")
            print(f"   4. Close and restart MT5 terminal")
            
            return False
            
    except Exception as e:
        print(f"❌ Python Error: {e}")
        return False

if __name__ == "__main__":
    test_specific_path()
    input("\nPress Enter to close...")