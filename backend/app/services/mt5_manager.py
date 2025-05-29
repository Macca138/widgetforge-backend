"""
MT5 Terminal Manager - Handles MT5 connections and data collection
"""
import MetaTrader5 as mt5
import os
import json
import time
import base64
import threading
from typing import Dict, List, Optional
from dataclasses import dataclass
from app.services.cache_service import set_account

@dataclass
class MT5Terminal:
    path: str
    login: str
    server: str
    label: str
    is_connected: bool = False
    last_update: float = 0
    error_message: str = ""

class MT5Manager:
    def __init__(self):
        self.terminals: Dict[str, MT5Terminal] = {}
        self.polling_active = False
        self.polling_thread = None
        
    def add_terminal(self, login: str, password: str, server: str, label: str, terminal_path: str) -> bool:
        """Add a new MT5 terminal configuration"""
        terminal = MT5Terminal(
            path=terminal_path,
            login=login,
            server=server,
            label=label
        )
        
        # Test connection
        if self._test_connection(terminal, password):
            self.terminals[login] = terminal
            return True
        return False
    
    def _test_connection(self, terminal: MT5Terminal, password: str) -> bool:
        """Test if we can connect to an MT5 terminal"""
        try:
            # Try to initialize with the terminal path
            exe_path = os.path.join(terminal.path, "terminal64.exe")
            if not os.path.exists(exe_path):
                terminal.error_message = f"Terminal executable not found: {exe_path}"
                return False
            
            # Initialize MT5
            if not mt5.initialize(path=exe_path):
                terminal.error_message = f"Failed to initialize: {mt5.last_error()}"
                return False
            
            # Try to login
            if not mt5.login(int(terminal.login), password=password, server=terminal.server):
                terminal.error_message = f"Login failed: {mt5.last_error()}"
                mt5.shutdown()
                return False
            
            # Test account info access
            account_info = mt5.account_info()
            if account_info is None:
                terminal.error_message = "Cannot retrieve account info"
                mt5.shutdown()
                return False
            
            terminal.is_connected = True
            terminal.error_message = ""
            mt5.shutdown()
            return True
            
        except Exception as e:
            terminal.error_message = f"Connection error: {str(e)}"
            return False
    
    def get_terminal_status(self) -> List[Dict]:
        """Get status of all configured terminals"""
        return [
            {
                "login": login,
                "label": terminal.label,
                "server": terminal.server,
                "connected": terminal.is_connected,
                "last_update": terminal.last_update,
                "error": terminal.error_message
            }
            for login, terminal in self.terminals.items()
        ]
    
    def collect_data_for_terminal(self, login: str, password: str) -> Optional[Dict]:
        """Collect data from a specific terminal"""
        if login not in self.terminals:
            return None
            
        terminal = self.terminals[login]
        
        try:
            # Initialize
            exe_path = os.path.join(terminal.path, "terminal64.exe")
            if not mt5.initialize(path=exe_path):
                terminal.error_message = f"Init failed: {mt5.last_error()}"
                terminal.is_connected = False
                return None
            
            # Login
            if not mt5.login(int(terminal.login), password=password, server=terminal.server):
                terminal.error_message = f"Login failed: {mt5.last_error()}"
                terminal.is_connected = False
                mt5.shutdown()
                return None
            
            # Get account info
            account_info = mt5.account_info()
            if account_info is None:
                terminal.error_message = "No account info"
                terminal.is_connected = False
                mt5.shutdown()
                return None
            
            # Get positions
            positions = mt5.positions_get()
            trades = []
            
            for pos in positions:
                trades.append({
                    "symbol": pos.symbol,
                    "type": "BUY" if pos.type == mt5.ORDER_TYPE_BUY else "SELL",
                    "volume": pos.volume,
                    "entry_price": pos.price_open,
                    "current_price": pos.price_current,
                    "profit": pos.profit,
                    "sl": pos.sl,
                    "tp": pos.tp,
                    "time": pos.time
                })
            
            # Prepare data
            data = {
                "login": terminal.login,
                "label": terminal.label,
                "balance": account_info.balance,
                "equity": account_info.equity,
                "margin": account_info.margin,
                "free_margin": account_info.margin_free,
                "margin_level": account_info.margin_level,
                "profit": account_info.profit,
                "trades": trades,
                "trade_count": len(trades),
                "timestamp": time.time()
            }
            
            # Update status
            terminal.is_connected = True
            terminal.last_update = time.time()
            terminal.error_message = ""
            
            # Cache the data
            set_account(login, data, expire=60)
            
            mt5.shutdown()
            return data
            
        except Exception as e:
            terminal.error_message = f"Data collection error: {str(e)}"
            terminal.is_connected = False
            try:
                mt5.shutdown()
            except:
                pass
            return None
    
    def start_polling(self, traders_config: List[Dict], interval: int = 5):
        """Start continuous polling of all configured terminals"""
        self.polling_active = True
        
        def poll_loop():
            while self.polling_active:
                for trader in traders_config:
                    login = trader["login"]
                    password = base64.b64decode(trader["password"]).decode()
                    
                    if login in self.terminals:
                        data = self.collect_data_for_terminal(login, password)
                        if data:
                            print(f"✅ Updated data for {trader['label']} ({login})")
                        else:
                            print(f"❌ Failed to update {trader['label']} ({login})")
                    
                    time.sleep(1)  # Small delay between terminals
                
                time.sleep(interval)
        
        self.polling_thread = threading.Thread(target=poll_loop, daemon=True)
        self.polling_thread.start()
    
    def stop_polling(self):
        """Stop the polling process"""
        self.polling_active = False
        if self.polling_thread:
            self.polling_thread.join(timeout=5)

# Global instance
mt5_manager = MT5Manager()