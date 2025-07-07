#!/usr/bin/env python3
"""
Clean reset of chart database to fix corruption issues
"""
import os
import sqlite3
import logging

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def reset_chart_database():
    """Completely reset the chart database"""
    # Get database path
    cache_dir = os.path.join(os.path.dirname(__file__), '..', '.cache')
    os.makedirs(cache_dir, exist_ok=True)
    db_path = os.path.join(cache_dir, 'chart_history.db')
    
    # Remove existing corrupted database
    if os.path.exists(db_path):
        os.remove(db_path)
        logger.info(f"Removed corrupted database: {db_path}")
    
    # Create fresh database
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Create clean table with proper constraints
    cursor.execute('''
        CREATE TABLE price_history (
            symbol TEXT NOT NULL,
            timestamp INTEGER NOT NULL,
            price REAL NOT NULL,
            PRIMARY KEY (symbol, timestamp)
        )
    ''')
    
    # Create index for faster queries
    cursor.execute('''
        CREATE INDEX idx_symbol_timestamp 
        ON price_history (symbol, timestamp DESC)
    ''')
    
    conn.commit()
    conn.close()
    
    logger.info(f"Created clean database: {db_path}")
    print("✅ Chart database reset successfully!")
    print("🔄 Please restart the chart collector to populate with fresh data")

if __name__ == "__main__":
    reset_chart_database()