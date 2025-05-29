"""
MT5 Connection Test Script
Used to test MT5 connections without permanent configuration
"""
import MetaTrader5 as mt5
import argparse
import os
import sys

def test_mt5_connection(terminal_id: int, login: str, password: str, server: str) -> bool:
    """Test MT5 connection and return success status"""
    terminal_path = f"C:/MT5Terminals/Account{terminal_id}"
    exe_path = os.path.join(terminal_path, "terminal64.exe")
    
    if not os.path.exists(exe_path):
        print(f"Terminal executable not found: {exe_path}", file=sys.stderr)
        return False
    
    try:
        # Initialize MT5
        if not mt5.initialize(path=exe_path):
            error = mt5.last_error()
            print(f"Failed to initialize MT5: {error}", file=sys.stderr)
            return False
        
        # Test login
        if not mt5.login(int(login), password=password, server=server):
            error = mt5.last_error()
            print(f"Login failed: {error}", file=sys.stderr)
            mt5.shutdown()
            return False
        
        # Test account info access
        account_info = mt5.account_info()
        if account_info is None:
            print("Cannot retrieve account information", file=sys.stderr)
            mt5.shutdown()
            return False
        
        # Success - print account details
        print(f"Connection successful!")
        print(f"Account: {account_info.login}")
        print(f"Balance: ${account_info.balance:.2f}")
        print(f"Equity: ${account_info.equity:.2f}")
        print(f"Server: {account_info.server}")
        print(f"Currency: {account_info.currency}")
        
        mt5.shutdown()
        return True
        
    except Exception as e:
        print(f"Connection test error: {str(e)}", file=sys.stderr)
        try:
            mt5.shutdown()
        except:
            pass
        return False

def main():
    parser = argparse.ArgumentParser(description="Test MT5 Connection")
    parser.add_argument("--terminal-id", type=int, required=True, help="Terminal ID (2-10)")
    parser.add_argument("--login", required=True, help="MT5 Login")
    parser.add_argument("--password", required=True, help="MT5 Password")
    parser.add_argument("--server", required=True, help="MT5 Server")
    
    args = parser.parse_args()
    
    success = test_mt5_connection(args.terminal_id, args.login, args.password, args.server)
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()