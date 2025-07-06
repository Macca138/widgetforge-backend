import MetaTrader5 as mt5
import sqlite3
import time
import os
import sys
from datetime import datetime, timedelta
import json
import logging

# Add backend directory to Python path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class ChartDataCollector:
    def __init__(self):
        # Database path - auto-creates in .cache directory
        cache_dir = os.path.join(os.path.dirname(__file__), '..', '..', '..', '.cache')
        os.makedirs(cache_dir, exist_ok=True)
        self.db_path = os.path.join(cache_dir, 'chart_history.db')
        
        # Initialize database
        self.init_database()
        
        # Load symbols from the same file as price ticker
        symbols_file = os.path.join(os.path.dirname(__file__), 'symbols.txt')
        with open(symbols_file, 'r') as f:
            self.symbols = [line.strip() for line in f if line.strip()]
        
        logger.info(f"Chart collector initialized with {len(self.symbols)} symbols")
        
    def init_database(self):
        """Create database and tables if they don't exist"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Create price history table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS price_history (
                symbol TEXT,
                timestamp INTEGER,
                price REAL,
                PRIMARY KEY (symbol, timestamp)
            )
        ''')
        
        # Create index for faster queries
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_symbol_timestamp 
            ON price_history (symbol, timestamp DESC)
        ''')
        
        conn.commit()
        conn.close()
        logger.info("Database initialized successfully")
    
    def connect_mt5(self):
        """Connect to MT5 terminal"""
        if not mt5.initialize(path="C:/MT5Terminals/Account1/terminal64.exe"):
            raise RuntimeError("MT5 initialization failed")
        logger.info("Connected to MT5")
    
    def collect_initial_history(self):
        """Collect 24 hours of historical data on startup"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        for symbol in self.symbols:
            try:
                # Get 15-minute bars for the last 24 hours (96 bars)
                rates = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_M15, 0, 96)
                
                if rates is None:
                    logger.warning(f"No historical data for {symbol}")
                    continue
                
                # Store close prices with timestamps
                for rate in rates:
                    timestamp = int(rate['time'])  # Ensure timestamp is an integer
                    price = float(rate['close'])   # Ensure price is a float
                    
                    cursor.execute('''
                        INSERT OR REPLACE INTO price_history (symbol, timestamp, price)
                        VALUES (?, ?, ?)
                    ''', (symbol, timestamp, price))
                
                logger.info(f"Collected {len(rates)} historical points for {symbol}")
                
            except Exception as e:
                logger.error(f"Error collecting history for {symbol}: {e}")
        
        conn.commit()
        conn.close()
    
    def update_prices(self):
        """Update current prices for all symbols"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        current_time = int(time.time())
        
        for symbol in self.symbols:
            try:
                tick = mt5.symbol_info_tick(symbol)
                if tick:
                    price = (tick.bid + tick.ask) / 2
                    
                    # Insert new price
                    cursor.execute('''
                        INSERT OR REPLACE INTO price_history (symbol, timestamp, price)
                        VALUES (?, ?, ?)
                    ''', (symbol, current_time, price))
                    
            except Exception as e:
                logger.error(f"Error updating {symbol}: {e}")
        
        conn.commit()
        conn.close()
    
    def cleanup_old_data(self):
        """Clean up data older than 25 hours (keep 24+ hours available)"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        current_time = int(time.time())
        cutoff = current_time - (25 * 60 * 60)  # Keep 25 hours, delete older
        
        result = cursor.execute('''
            DELETE FROM price_history 
            WHERE timestamp < ?
        ''', (cutoff,))
        
        deleted_count = result.rowcount
        conn.commit()
        conn.close()
        logger.info(f"Cleaned up {deleted_count} old data points (older than 25 hours)")
    
    def get_chart_data(self, symbol, hours=24, max_points=180):
        """Get resampled chart data for a symbol"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cutoff = int(time.time()) - (hours * 60 * 60)
        
        cursor.execute('''
            SELECT timestamp, price 
            FROM price_history 
            WHERE symbol = ? AND timestamp > ?
            ORDER BY timestamp
        ''', (symbol, cutoff))
        
        data = cursor.fetchall()
        conn.close()
        
        if not data:
            return []
        
        # Resample if we have too many points
        if len(data) > max_points:
            step = len(data) // max_points
            data = data[::step]
        
        return [{'timestamp': ts, 'price': price} for ts, price in data]
    
    def run(self):
        """Main run loop"""
        try:
            self.connect_mt5()
            
            # Collect initial history
            logger.info("Collecting initial 24-hour history...")
            self.collect_initial_history()
            
            # Update loop - every 8 minutes for ~180 points per day
            update_interval = 8 * 60  # 8 minutes in seconds
            cleanup_counter = 0
            
            while True:
                try:
                    self.update_prices()
                    logger.info(f"Updated prices for {len(self.symbols)} symbols")
                    
                    # Run cleanup every 7 updates (roughly every hour)
                    cleanup_counter += 1
                    if cleanup_counter >= 7:
                        self.cleanup_old_data()
                        cleanup_counter = 0
                    
                    time.sleep(update_interval)
                    
                except Exception as e:
                    logger.error(f"Error in update loop: {e}")
                    time.sleep(60)  # Wait a minute before retry
                    
        except KeyboardInterrupt:
            logger.info("Chart collector stopped by user")
        except Exception as e:
            logger.error(f"Fatal error: {e}")
        finally:
            mt5.shutdown()

if __name__ == "__main__":
    collector = ChartDataCollector()
    collector.run()