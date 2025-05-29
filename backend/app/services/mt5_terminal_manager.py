"""
MT5 Terminal Manager - Production Version
Handles persistent connections, separate processes, and robust error handling
"""
import json
import os
import time
import base64
import subprocess
import signal
import threading
from datetime import datetime, date
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict
from cryptography.fernet import Fernet
from app.services.cache_service import set_account, get_account
import psutil

@dataclass
class TerminalConfig:
    terminal_id: int
    login: str
    server: str
    label: str
    encrypted_password: str
    is_active: bool = False
    is_connected: bool = False
    last_update: float = 0
    error_message: str = ""
    retry_count: int = 0
    process_pid: Optional[int] = None

@dataclass
class TradeData:
    ticket: int
    symbol: str
    trade_type: str
    volume: float
    entry_price: float
    current_price: float
    profit: float
    sl: float
    tp: float
    open_time: str
    duration_minutes: int

@dataclass
class DailyStats:
    date: str
    total_profit: float
    total_trades: int
    winning_trades: int
    losing_trades: int
    win_rate: float
    largest_win: float
    largest_loss: float

class MT5TerminalManager:
    def __init__(self):
        self.terminals: Dict[int, TerminalConfig] = {}
        self.base_path = "C:/MT5Terminals"
        self.cache_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", ".cache"))
        self.config_file = os.path.join(self.cache_dir, "mt5_terminals.json")
        self.encryption_key_file = os.path.join(self.cache_dir, "mt5_key.key")
        self.processes: Dict[int, subprocess.Popen] = {}
        
        # Ensure cache directory exists
        os.makedirs(self.cache_dir, exist_ok=True)
        
        # Initialize encryption
        self._init_encryption()
        
        # Load existing configuration
        self._load_configuration()
    
    def _init_encryption(self):
        """Initialize encryption for password storage"""
        if os.path.exists(self.encryption_key_file):
            with open(self.encryption_key_file, 'rb') as f:
                self.encryption_key = f.read()
        else:
            self.encryption_key = Fernet.generate_key()
            with open(self.encryption_key_file, 'wb') as f:
                f.write(self.encryption_key)
        
        self.cipher = Fernet(self.encryption_key)
    
    def _encrypt_password(self, password: str) -> str:
        """Encrypt password for secure storage"""
        return self.cipher.encrypt(password.encode()).decode()
    
    def _decrypt_password(self, encrypted_password: str) -> str:
        """Decrypt password for use"""
        return self.cipher.decrypt(encrypted_password.encode()).decode()
    
    def _load_configuration(self):
        """Load existing terminal configurations"""
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r') as f:
                    data = json.load(f)
                
                for terminal_data in data.get('terminals', []):
                    config = TerminalConfig(**terminal_data)
                    self.terminals[config.terminal_id] = config
                    
                print(f"✅ Loaded {len(self.terminals)} terminal configurations")
            except Exception as e:
                print(f"⚠️ Failed to load configuration: {e}")
    
    def _save_configuration(self):
        """Save terminal configurations to disk"""
        try:
            data = {
                'terminals': [asdict(config) for config in self.terminals.values()],
                'last_updated': datetime.now().isoformat()
            }
            
            with open(self.config_file, 'w') as f:
                json.dump(data, f, indent=2)
                
            print("✅ Configuration saved")
        except Exception as e:
            print(f"❌ Failed to save configuration: {e}")
    
    def get_available_terminals(self) -> List[int]:
        """Get list of available terminal slots (2-10)"""
        available = []
        for terminal_id in range(2, 11):
            terminal_path = os.path.join(self.base_path, f"Account{terminal_id}")
            if os.path.exists(terminal_path):
                available.append(terminal_id)
        return available
    
    def get_terminal_status(self) -> List[Dict]:
        """Get status of all configured terminals"""
        status_list = []
        
        for terminal_id, config in self.terminals.items():
            # Check if process is still running
            if config.process_pid:
                try:
                    process = psutil.Process(config.process_pid)
                    process_running = process.is_running()
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    process_running = False
                    config.process_pid = None
            else:
                process_running = False
            
            status_list.append({
                'terminal_id': terminal_id,
                'label': config.label,
                'login': config.login,
                'server': config.server,
                'is_active': config.is_active,
                'is_connected': config.is_connected,
                'process_running': process_running,
                'last_update': config.last_update,
                'error_message': config.error_message,
                'retry_count': config.retry_count
            })
        
        return status_list
    
    def add_terminal(self, terminal_id: int, login: str, password: str, server: str, label: str) -> Tuple[bool, str]:
        """Add a new terminal configuration"""
        # Validate terminal exists
        terminal_path = os.path.join(self.base_path, f"Account{terminal_id}")
        if not os.path.exists(terminal_path):
            return False, f"Terminal path not found: {terminal_path}"
        
        # Check if terminal is already configured
        if terminal_id in self.terminals:
            return False, f"Terminal {terminal_id} is already configured"
        
        # Encrypt password
        encrypted_password = self._encrypt_password(password)
        
        # Create configuration
        config = TerminalConfig(
            terminal_id=terminal_id,
            login=login,
            server=server,
            label=label,
            encrypted_password=encrypted_password
        )
        
        self.terminals[terminal_id] = config
        self._save_configuration()
        
        return True, f"Terminal {terminal_id} configured successfully"
    
    def connect_terminal(self, terminal_id: int) -> Tuple[bool, str]:
        """Connect a specific terminal"""
        if terminal_id not in self.terminals:
            return False, "Terminal not configured"
        
        config = self.terminals[terminal_id]
        
        # Start the poller process
        success, message = self._start_terminal_process(terminal_id)
        
        if success:
            config.is_active = True
            config.error_message = ""
            config.retry_count = 0
            self._save_configuration()
        
        return success, message
    
    def disconnect_terminal(self, terminal_id: int) -> Tuple[bool, str]:
        """Disconnect a specific terminal"""
        if terminal_id not in self.terminals:
            return False, "Terminal not configured"
        
        config = self.terminals[terminal_id]
        
        # Stop the process
        if config.process_pid:
            try:
                if terminal_id in self.processes:
                    self.processes[terminal_id].terminate()
                    self.processes[terminal_id].wait(timeout=5)
                    del self.processes[terminal_id]
                else:
                    # Try to kill by PID
                    process = psutil.Process(config.process_pid)
                    process.terminate()
                    process.wait(timeout=5)
            except Exception as e:
                print(f"⚠️ Error stopping process for terminal {terminal_id}: {e}")
        
        config.is_active = False
        config.is_connected = False
        config.process_pid = None
        config.error_message = ""
        config.retry_count = 0
        
        self._save_configuration()
        
        return True, f"Terminal {terminal_id} disconnected"
    
    def remove_terminal(self, terminal_id: int) -> Tuple[bool, str]:
        """Remove a terminal configuration completely"""
        if terminal_id not in self.terminals:
            return False, "Terminal not configured"
        
        # First disconnect if active
        if self.terminals[terminal_id].is_active:
            self.disconnect_terminal(terminal_id)
        
        # Remove from configuration
        del self.terminals[terminal_id]
        self._save_configuration()
        
        return True, f"Terminal {terminal_id} removed"
    
    def _start_terminal_process(self, terminal_id: int) -> Tuple[bool, str]:
        """Start the polling process for a terminal"""
        config = self.terminals[terminal_id]
        
        try:
            # Script path for the individual terminal poller
            script_path = os.path.join(os.path.dirname(__file__), "..", "pollers", "terminal_poller.py")
            
            # Start the process
            process = subprocess.Popen([
                "python", script_path,
                "--terminal-id", str(terminal_id),
                "--login", config.login,
                "--password", self._decrypt_password(config.encrypted_password),
                "--server", config.server,
                "--label", config.label
            ])
            
            config.process_pid = process.pid
            self.processes[terminal_id] = process
            
            return True, f"Started process for terminal {terminal_id} (PID: {process.pid})"
            
        except Exception as e:
            return False, f"Failed to start process: {str(e)}"
    
    def test_connection(self, login: str, password: str, server: str) -> Tuple[bool, str]:
        """Test MT5 connection without saving configuration"""
        # Find an available terminal for testing
        available_terminals = self.get_available_terminals()
        if not available_terminals:
            return False, "No MT5 terminals available for testing"
        
        # Use the first available terminal that's not configured
        test_terminal = None
        for terminal_id in available_terminals:
            if terminal_id not in self.terminals:
                test_terminal = terminal_id
                break
        
        if test_terminal is None:
            # All terminals are configured, use the first one temporarily
            test_terminal = available_terminals[0]
        
        # Test script path
        script_path = os.path.join(os.path.dirname(__file__), "..", "pollers", "test_connection.py")
        
        try:
            result = subprocess.run([
                "python", script_path,
                "--terminal-id", str(test_terminal),
                "--login", login,
                "--password", password,
                "--server", server
            ], capture_output=True, text=True, timeout=30)
            
            if result.returncode == 0:
                return True, "Connection successful"
            else:
                return False, result.stderr or "Connection failed"
                
        except subprocess.TimeoutExpired:
            return False, "Connection test timed out"
        except Exception as e:
            return False, f"Test failed: {str(e)}"
    
    def get_active_terminals(self) -> List[Dict]:
        """Get list of active terminals for widget configuration"""
        active = []
        for terminal_id, config in self.terminals.items():
            if config.is_active and config.is_connected:
                active.append({
                    'terminal_id': terminal_id,
                    'label': config.label,
                    'login': config.login
                })
        return active
    
    def get_terminal_data(self, terminal_id: int) -> Optional[Dict]:
        """Get cached data for a specific terminal"""
        return get_account(f"terminal_{terminal_id}")
    
    def get_daily_stats(self, terminal_id: int, target_date: str = None) -> Optional[DailyStats]:
        """Get daily trading statistics for a terminal"""
        if target_date is None:
            target_date = date.today().isoformat()
        
        # Load from cache or calculate
        cache_key = f"daily_stats_{terminal_id}_{target_date}"
        cached_stats = get_account(cache_key)
        
        if cached_stats:
            return DailyStats(**cached_stats)
        
        return None

# Global instance
mt5_terminal_manager = MT5TerminalManager()