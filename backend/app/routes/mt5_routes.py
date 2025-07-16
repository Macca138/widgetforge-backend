"""
MT5 Routes - Price Data Only
"""
from fastapi import APIRouter, HTTPException
import os
import sqlite3

router = APIRouter()

@router.get("/api/mt5/chart-history/{symbol}")
async def get_chart_history(symbol: str, hours: int = 24, max_points: int = 180):
    """Get historical chart data for a symbol"""
    try:
        # Connect to the chart history database
        cache_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", ".cache"))
        db_path = os.path.join(cache_dir, "chart_history.db")
        
        # Debug info
        import logging
        logging.info(f"Looking for database at: {db_path}")
        logging.info(f"Database exists: {os.path.exists(db_path)}")
        
        if not os.path.exists(db_path):
            # Try alternative path
            alt_cache_dir = os.path.join(os.getcwd(), ".cache")
            alt_db_path = os.path.join(alt_cache_dir, "chart_history.db")
            logging.info(f"Trying alternative path: {alt_db_path}")
            
            if os.path.exists(alt_db_path):
                db_path = alt_db_path
            else:
                raise HTTPException(status_code=404, detail=f"Chart history database not found. Searched: {db_path} and {alt_db_path}")
        
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Calculate cutoff timestamp
        import time
        cutoff = int(time.time()) - (hours * 60 * 60)
        
        # Query data
        cursor.execute('''
            SELECT timestamp, price 
            FROM price_history 
            WHERE symbol = ? AND timestamp > ?
            ORDER BY timestamp
        ''', (symbol, cutoff))
        
        data = cursor.fetchall()
        conn.close()
        
        if not data:
            return {"symbol": symbol, "data": [], "message": "No data available for this symbol"}
        
        # Resample if we have too many points
        if len(data) > max_points:
            step = len(data) // max_points
            data = data[::step]
        
        # Format response with safe data conversion
        chart_data = []
        for ts, price in data:
            try:
                # Ensure timestamp and price are proper numbers
                timestamp = int(ts) if isinstance(ts, (int, float)) else int(float(ts))
                price_val = float(price) if isinstance(price, (int, float, str)) else 0.0
                chart_data.append({"timestamp": timestamp, "price": price_val})
            except (ValueError, TypeError) as e:
                logging.warning(f"Skipping invalid data point: ts={ts}, price={price}, error={e}")
                continue
        
        if not chart_data:
            return {"symbol": symbol, "data": [], "message": "No valid data points found"}
        
        return {
            "symbol": symbol,
            "data": chart_data,
            "first_price": chart_data[0]["price"] if chart_data else None,
            "last_price": chart_data[-1]["price"] if chart_data else None,
            "point_count": len(chart_data)
        }
        
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)} | {error_details}")