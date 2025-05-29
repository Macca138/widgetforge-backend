"""
Individual Terminal Poller - Separate Process for Each MT5 Terminal
This script runs as a separate process for each active MT5 terminal
"""
import MetaTrader5 as mt5
import argparse
import time
import json
import os
import sys
from datetime import datetime, date
from typing import Dict, List, Optional

# Add the parent directory to sys.path to import cache_service
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from services.cache_service import set_account

class TerminalPoller:
    def __init__(self, terminal_id: int, login: str, password: str, server: str, label: str):
        self.terminal_id = terminal_id
        self.login = login
        self.password = password
        self.server = server
        self.label = label
        self.terminal_path = f"C:/MT5Terminals/Account{terminal_id}"
        self.exe_path = os.path.join(self.terminal_path, "terminal64.exe")
        self.is_connected = False
        self.retry_count = 0
        self.max_retries = 5
        self.daily_trades = []
        
        print(f"🚀 Starting poller for {label} (Terminal {terminal_id}, Login {login})")
    
    def connect(self) -> bool:
        """Connect to MT5 terminal"""
        try:
            # Initialize MT5 with the specific terminal
            if not mt5.initialize(path=self.exe_path):
                error = mt5.last_error()
                print(f"❌ Failed to initialize MT5 for terminal {self.terminal_id}: {error}")
                return False
            
            # Login to the account
            if not mt5.login(int(self.login), password=self.password, server=self.server):
                error = mt5.last_error()
                print(f"❌ Login failed for {self.label}: {error}")
                mt5.shutdown()
                return False
            
            print(f"✅ Connected to {self.label} on terminal {self.terminal_id}")
            self.is_connected = True
            self.retry_count = 0
            
            # Update connection status in cache
            self._update_connection_status(True, "")
            
            return True
            
        except Exception as e:
            print(f"❌ Connection error for {self.label}: {str(e)}")
            self._update_connection_status(False, str(e))
            return False
    
    def disconnect(self):
        """Disconnect from MT5"""
        try:
            if self.is_connected:
                mt5.shutdown()
                self.is_connected = False
                print(f"🔌 Disconnected from {self.label}")
        except Exception as e:
            print(f"⚠️ Error during disconnect: {e}")
    
    def _update_connection_status(self, connected: bool, error_message: str):
        """Update connection status in cache"""
        status_data = {
            'terminal_id': self.terminal_id,
            'is_connected': connected,
            'last_update': time.time(),
            'error_message': error_message,
            'retry_count': self.retry_count
        }
        set_account(f"terminal_status_{self.terminal_id}", status_data, expire=300)
    
    def collect_data(self) -> Optional[Dict]:
        """Collect account and trade data"""
        if not self.is_connected:
            return None
        
        try:
            # Get account information
            account_info = mt5.account_info()
            if account_info is None:
                print(f"⚠️ No account info for {self.label}")
                return None
            
            # Get positions (open trades)
            positions = mt5.positions_get()
            open_trades = []
            
            for pos in positions:
                trade_data = {
                    'ticket': pos.ticket,
                    'symbol': pos.symbol,
                    'type': 'BUY' if pos.type == mt5.ORDER_TYPE_BUY else 'SELL',
                    'volume': pos.volume,
                    'entry_price': pos.price_open,
                    'current_price': pos.price_current,
                    'profit': pos.profit,
                    'sl': pos.sl,
                    'tp': pos.tp,
                    'open_time': datetime.fromtimestamp(pos.time).isoformat(),
                    'duration_minutes': int((time.time() - pos.time) / 60)
                }
                open_trades.append(trade_data)
            
            # Get today's deal history (closed trades)
            today = date.today()
            deals = mt5.history_deals_get(today, datetime.now())
            closed_trades_today = []
            
            if deals:
                for deal in deals:
                    if deal.type in [mt5.DEAL_TYPE_BUY, mt5.DEAL_TYPE_SELL]:
                        trade_data = {
                            'ticket': deal.ticket,
                            'symbol': deal.symbol,
                            'type': 'BUY' if deal.type == mt5.DEAL_TYPE_BUY else 'SELL',
                            'volume': deal.volume,
                            'price': deal.price,
                            'profit': deal.profit,
                            'time': datetime.fromtimestamp(deal.time).isoformat(),
                            'commission': deal.commission,
                            'swap': deal.swap
                        }
                        closed_trades_today.append(trade_data)
            
            # Calculate daily statistics
            daily_stats = self._calculate_daily_stats(closed_trades_today)
            
            # Prepare complete data
            complete_data = {
                'terminal_id': self.terminal_id,
                'label': self.label,
                'login': self.login,
                'balance': account_info.balance,
                'equity': account_info.equity,
                'margin': account_info.margin,
                'free_margin': account_info.margin_free,
                'margin_level': account_info.margin_level if account_info.margin > 0 else 0,
                'profit': account_info.profit,
                'currency': account_info.currency,
                'open_trades': open_trades,
                'closed_trades_today': closed_trades_today,
                'daily_stats': daily_stats,
                'trade_count': len(open_trades),
                'timestamp': time.time(),
                'last_update': datetime.now().isoformat()
            }
            
            # Cache the data
            set_account(f"terminal_{self.terminal_id}", complete_data, expire=60)
            
            return complete_data
            
        except Exception as e:
            print(f"❌ Data collection error for {self.label}: {str(e)}")
            self._update_connection_status(False, str(e))
            return None
    
    def _calculate_daily_stats(self, closed_trades: List[Dict]) -> Dict:
        """Calculate daily trading statistics"""
        if not closed_trades:
            return {
                'date': date.today().isoformat(),
                'total_profit': 0,
                'total_trades': 0,
                'winning_trades': 0,
                'losing_trades': 0,
                'win_rate': 0,
                'largest_win': 0,
                'largest_loss': 0
            }
        
        total_profit = sum(trade['profit'] for trade in closed_trades)
        winning_trades = [trade for trade in closed_trades if trade['profit'] > 0]
        losing_trades = [trade for trade in closed_trades if trade['profit'] < 0]
        
        largest_win = max((trade['profit'] for trade in winning_trades), default=0)
        largest_loss = min((trade['profit'] for trade in losing_trades), default=0)
        
        win_rate = (len(winning_trades) / len(closed_trades)) * 100 if closed_trades else 0
        
        stats = {
            'date': date.today().isoformat(),
            'total_profit': total_profit,
            'total_trades': len(closed_trades),
            'winning_trades': len(winning_trades),
            'losing_trades': len(losing_trades),
            'win_rate': round(win_rate, 2),
            'largest_win': largest_win,
            'largest_loss': largest_loss
        }
        
        # Cache daily stats separately
        set_account(f"daily_stats_{self.terminal_id}_{stats['date']}", stats, expire=86400)  # 24 hours
        
        return stats
    
    def run_polling_loop(self):
        """Main polling loop"""
        while True:
            try:
                # Check connection
                if not self.is_connected:
                    print(f"🔄 Attempting to connect {self.label}...")
                    if not self.connect():
                        self.retry_count += 1
                        if self.retry_count >= self.max_retries:
                            print(f"❌ Max retries reached for {self.label}. Sleeping for 5 minutes...")
                            time.sleep(300)  # Sleep 5 minutes before resetting retry count
                            self.retry_count = 0
                        else:
                            wait_time = min(5 * (2 ** self.retry_count), 60)  # Exponential backoff, max 60s
                            print(f"⏳ Retry {self.retry_count}/{self.max_retries} in {wait_time}s...")
                            time.sleep(wait_time)
                        continue
                
                # Collect data
                data = self.collect_data()
                if data:
                    print(f"✅ Updated {self.label}: Balance ${data['balance']:.2f}, Equity ${data['equity']:.2f}, Trades: {data['trade_count']}")
                else:
                    print(f"⚠️ Failed to collect data for {self.label}")
                    self.is_connected = False  # Force reconnection attempt
                
                # Sleep before next poll
                time.sleep(5)  # Poll every 5 seconds
                
            except KeyboardInterrupt:
                print(f"🛑 Stopping poller for {self.label}")
                break
            except Exception as e:
                print(f"❌ Unexpected error in polling loop for {self.label}: {str(e)}")
                self.is_connected = False
                time.sleep(10)
        
        # Cleanup on exit
        self.disconnect()

def main():
    parser = argparse.ArgumentParser(description="MT5 Terminal Poller")
    parser.add_argument("--terminal-id", type=int, required=True, help="Terminal ID (2-10)")
    parser.add_argument("--login", required=True, help="MT5 Login")
    parser.add_argument("--password", required=True, help="MT5 Password")
    parser.add_argument("--server", required=True, help="MT5 Server")
    parser.add_argument("--label", required=True, help="Trader Label")
    
    args = parser.parse_args()
    
    # Create and run the poller
    poller = TerminalPoller(
        terminal_id=args.terminal_id,
        login=args.login,
        password=args.password,
        server=args.server,
        label=args.label
    )
    
    try:
        poller.run_polling_loop()
    except KeyboardInterrupt:
        print("🛑 Poller stopped by user")
    finally:
        poller.disconnect()

if __name__ == "__main__":
    main()