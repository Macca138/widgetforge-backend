#!/usr/bin/env python3
"""
Reset Chart Database Script
This script will delete the corrupted chart database and recreate it with proper data types.
"""

import os
import sqlite3
from pathlib import Path

def reset_chart_database():
    """Reset the chart history database to fix binary timestamp issues"""
    
    # Get the database path
    backend_dir = Path(__file__).parent
    cache_dir = backend_dir.parent / ".cache"
    db_path = cache_dir / "chart_history.db"
    
    print(f"Looking for database at: {db_path}")
    
    # Delete existing database if it exists
    if db_path.exists():
        print(f"Deleting corrupted database: {db_path}")
        os.remove(db_path)
    else:
        print("Database not found (this is OK)")
    
    # Create cache directory if it doesn't exist
    cache_dir.mkdir(parents=True, exist_ok=True)
    
    # Create new database with proper schema
    print("Creating new database with proper schema...")
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()
    
    # Create price history table with proper data types
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS price_history (
            symbol TEXT NOT NULL,
            timestamp INTEGER NOT NULL,
            price REAL NOT NULL,
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
    
    print("✅ New database created successfully!")
    print("\nNext steps:")
    print("1. Stop the chart collector service if running")
    print("2. Restart the chart collector service")
    print("3. Wait 5-10 minutes for historical data to be collected")
    print("4. Test the API endpoint: /api/mt5/chart-history/EURUSD")

if __name__ == "__main__":
    reset_chart_database()