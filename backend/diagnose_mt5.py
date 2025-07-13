#!/usr/bin/env python3
"""
MT5 Connection Diagnostic Script
Helps identify the correct MT5 terminal path and configuration
"""

import MetaTrader5 as mt5
import os
import sys
from pathlib import Path

def find_mt5_installations():
    """Find common MT5 installation paths"""
    common_paths = [
        # Standard installations
        "C:/Program Files/MetaTrader 5/terminal64.exe",
        "C:/Program Files (x86)/MetaTrader 5/terminal64.exe",
        "C:/Users/{}/AppData/Roaming/MetaQuotes/Terminal/*/terminal64.exe".format(os.getenv('USERNAME')),
        
        # Custom terminal paths (like in your poller)
        "C:/MT5Terminals/Account1/terminal64.exe",
        "C:/MT5Terminals/Account2/terminal64.exe",
        "C:/MT5Terminals/Account3/terminal64.exe",
        
        # Desktop installations
        "C:/Users/{}/Desktop/MetaTrader 5/terminal64.exe".format(os.getenv('USERNAME')),
        
        # Broker-specific installations
        "C:/Program Files/*/terminal64.exe",
    ]
    
    found_paths = []
    
    print("🔍 Searching for MT5 installations...")
    print()
    
    for path_pattern in common_paths:
        if '*' in path_pattern:
            # Handle wildcard paths
            try:
                from glob import glob
                matches = glob(path_pattern)
                for match in matches:
                    if os.path.exists(match):
                        found_paths.append(match)
                        print(f"✅ Found: {match}")
            except:
                pass
        else:
            # Handle exact paths
            if os.path.exists(path_pattern):
                found_paths.append(path_pattern)
                print(f"✅ Found: {path_pattern}")
    
    if not found_paths:
        print("❌ No MT5 installations found in common locations")
        print("\n💡 Try manually locating terminal64.exe on your system")
    
    return found_paths

def test_mt5_connection(terminal_path=None):
    """Test MT5 connection with optional terminal path"""
    print(f"\n🔌 Testing MT5 connection...")
    
    if terminal_path:
        print(f"   Using path: {terminal_path}")
        success = mt5.initialize(path=terminal_path)
    else:
        print(f"   Using default path (auto-detect)")
        success = mt5.initialize()
    
    if success:
        # Get terminal info
        terminal_info = mt5.terminal_info()
        account_info = mt5.account_info()
        
        print("✅ MT5 Connection Successful!")
        print(f"   Terminal: {terminal_info.name if terminal_info else 'Unknown'}")
        print(f"   Path: {terminal_info.path if terminal_info else 'Unknown'}")
        print(f"   Account: {account_info.login if account_info else 'Not logged in'}")
        print(f"   Server: {account_info.server if account_info else 'No server'}")
        print(f"   Balance: ${account_info.balance if account_info else 'N/A'}")
        
        # Test symbol access
        symbols = mt5.symbols_get()
        if symbols:
            print(f"   Symbols available: {len(symbols)}")
        else:
            print("   ⚠️ No symbols available (may need to login to trading account)")
        
        mt5.shutdown()
        return True
    else:
        error = mt5.last_error()
        print(f"❌ MT5 Connection Failed!")
        print(f"   Error: {error}")
        return False

def main():
    print("=" * 60)
    print("          MT5 CONNECTION DIAGNOSTIC TOOL")
    print("=" * 60)
    print()
    
    # Step 1: Find MT5 installations
    found_paths = find_mt5_installations()
    
    print("\n" + "=" * 60)
    
    # Step 2: Test default connection first
    print("📋 TESTING CONNECTIONS")
    print("=" * 60)
    
    print("\n1️⃣ Testing default MT5 connection (auto-detect)...")
    if test_mt5_connection():
        print("\n🎉 Success with default connection!")
        print("💡 You can use: mt5.initialize() in your poller")
        return
    
    # Step 3: Test found installations
    if found_paths:
        print("\n2️⃣ Testing found MT5 installations...")
        for i, path in enumerate(found_paths, 1):
            print(f"\n   Test {i}: {path}")
            if test_mt5_connection(path):
                print(f"\n🎉 Success with: {path}")
                print(f"💡 Update your poller to use this path:")
                print(f"    mt5.initialize(path=\"{path}\")")
                return
    
    # Step 4: Manual guidance
    print("\n" + "=" * 60)
    print("🛠️  MANUAL TROUBLESHOOTING")
    print("=" * 60)
    print()
    print("If all tests failed, try these steps:")
    print()
    print("1. 🔍 Find terminal64.exe manually:")
    print("   - Open File Explorer")
    print("   - Search for 'terminal64.exe' in C: drive")
    print("   - Note the full path")
    print()
    print("2. ✅ Verify MT5 is running:")
    print("   - Open MetaTrader 5 application")
    print("   - Login to your trading account")
    print("   - Ensure it's not just the installer")
    print()
    print("3. 🔧 Check permissions:")
    print("   - Run this script as Administrator")
    print("   - Ensure MT5 allows DLL imports (Tools > Options > Expert Advisors)")
    print()
    print("4. 📝 Update poller_market.py:")
    print("   - Replace the hardcoded path with the correct one")
    print("   - Or use mt5.initialize() without path for auto-detect")
    print()

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"\n❌ Diagnostic script error: {e}")
        print("💡 Make sure MetaTrader5 package is installed: pip install MetaTrader5")
    
    print("\n" + "=" * 60)
    input("Press Enter to close...")