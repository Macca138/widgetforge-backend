#!/usr/bin/env python3
"""
Test Chart API Script
Test the chart history API endpoint to verify data collection works correctly.
"""

import requests
import json
from pathlib import Path
import sqlite3
import time

def test_database_direct():
    """Test database directly"""
    print("=== Testing Database Directly ===")
    
    # Get database path
    backend_dir = Path(__file__).parent
    cache_dir = backend_dir.parent / ".cache"
    db_path = cache_dir / "chart_history.db"
    
    print(f"Database path: {db_path}")
    print(f"Database exists: {db_path.exists()}")
    
    if not db_path.exists():
        print("❌ Database not found - start the chart collector first")
        return False
    
    # Connect and query
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()
    
    # Check table structure
    cursor.execute("PRAGMA table_info(price_history)")
    columns = cursor.fetchall()
    print(f"Table columns: {columns}")
    
    # Count total records
    cursor.execute("SELECT COUNT(*) FROM price_history")
    total_count = cursor.fetchone()[0]
    print(f"Total records in database: {total_count}")
    
    # Check unique symbols
    cursor.execute("SELECT DISTINCT symbol FROM price_history")
    symbols = [row[0] for row in cursor.fetchall()]
    print(f"Symbols in database: {symbols}")
    
    # Check sample data for first symbol
    if symbols:
        symbol = symbols[0]
        cursor.execute("""
            SELECT timestamp, price, datetime(timestamp, 'unixepoch') as readable_time
            FROM price_history 
            WHERE symbol = ? 
            ORDER BY timestamp DESC 
            LIMIT 5
        """, (symbol,))
        
        sample_data = cursor.fetchall()
        print(f"\nSample data for {symbol}:")
        for row in sample_data:
            print(f"  Timestamp: {row[0]}, Price: {row[1]}, Time: {row[2]}")
    
    conn.close()
    return total_count > 0

def test_api_endpoint():
    """Test the API endpoint"""
    print("\n=== Testing API Endpoint ===")
    
    # Test endpoint
    url = "http://localhost:8000/api/mt5/chart-history/EURUSD"
    
    try:
        response = requests.get(url, timeout=10)
        print(f"Status code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"Symbol: {data.get('symbol')}")
            print(f"Data points: {data.get('point_count', 0)}")
            
            if data.get('data'):
                print(f"First price: {data.get('first_price')}")
                print(f"Last price: {data.get('last_price')}")
                print(f"Sample data points:")
                for i, point in enumerate(data['data'][:3]):
                    readable_time = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(point['timestamp']))
                    print(f"  {i+1}. Time: {readable_time}, Price: {point['price']}")
                
                return len(data['data']) > 1
            else:
                print("❌ No data points returned")
                return False
        else:
            print(f"❌ API request failed: {response.text}")
            return False
            
    except requests.exceptions.RequestException as e:
        print(f"❌ API request failed: {e}")
        return False

def main():
    """Run all tests"""
    print("Chart API Test Script")
    print("=" * 40)
    
    # Test database
    db_has_data = test_database_direct()
    
    # Test API
    api_works = test_api_endpoint()
    
    print("\n" + "=" * 40)
    print("TEST RESULTS:")
    print(f"Database has data: {'✅' if db_has_data else '❌'}")
    print(f"API returns data: {'✅' if api_works else '❌'}")
    
    if db_has_data and api_works:
        print("\n🎉 All tests passed! Mini charts should work correctly.")
    else:
        print("\n⚠️  Some tests failed. Check the chart collector service.")

if __name__ == "__main__":
    main()