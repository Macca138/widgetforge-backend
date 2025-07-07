"""
MT5 Terminal Management Routes
"""
from fastapi import APIRouter, HTTPException, Header, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import List, Optional
import json
import os
import base64
import sqlite3
from app.services.mt5_manager import mt5_manager
from app.services.cache_service import get_account

router = APIRouter()

class TraderConfig(BaseModel):
    login: str
    password: str
    server: str
    label: str

class TestConnectionRequest(BaseModel):
    login: str
    password: str
    server: str
    terminal_path: str

@router.post("/api/mt5/test-connection")
async def test_mt5_connection(request: TestConnectionRequest, x_api_key: str = Header(None)):
    """Test connection to a single MT5 terminal"""
    # Auth check would go here
    
    # Find available terminal path
    base_terminals_dir = "C:/MT5Terminals"
    terminal_path = None
    
    # Check for available terminal slots (Account2-Account10)
    for i in range(2, 11):
        path = f"{base_terminals_dir}/Account{i}"
        if os.path.exists(path):
            terminal_path = path
            break
    
    if not terminal_path:
        raise HTTPException(status_code=400, detail="No available MT5 terminal slots found")
    
    # Test the connection
    success = mt5_manager.add_terminal(
        login=request.login,
        password=request.password,
        server=request.server,
        label=f"Test_{request.login}",
        terminal_path=terminal_path
    )
    
    if success:
        return {"status": "success", "message": "Connection successful", "terminal_path": terminal_path}
    else:
        terminal_status = mt5_manager.get_terminal_status()
        error_msg = "Connection failed"
        for status in terminal_status:
            if status["login"] == request.login:
                error_msg = status["error"]
                break
        
        raise HTTPException(status_code=400, detail=error_msg)

@router.get("/api/mt5/terminal-status")
async def get_terminal_status(x_api_key: str = Header(None)):
    """Get status of all configured MT5 terminals"""
    return {"terminals": mt5_manager.get_terminal_status()}

@router.post("/api/mt5/configure-traders")
async def configure_traders(traders: List[TraderConfig], x_api_key: str = Header(None)):
    """Configure multiple trader accounts"""
    
    if len(traders) > 9:
        raise HTTPException(status_code=400, detail="Maximum 9 traders allowed")
    
    # Stop any existing polling
    mt5_manager.stop_polling()
    
    # Clear existing terminals
    mt5_manager.terminals.clear()
    
    base_terminals_dir = "C:/MT5Terminals"
    configured_traders = []
    
    for i, trader in enumerate(traders):
        terminal_path = f"{base_terminals_dir}/Account{i + 2}"
        
        if not os.path.exists(terminal_path):
            raise HTTPException(
                status_code=400, 
                detail=f"Terminal path not found: {terminal_path}"
            )
        
        # Test connection
        success = mt5_manager.add_terminal(
            login=trader.login,
            password=trader.password,
            server=trader.server,
            label=trader.label,
            terminal_path=terminal_path
        )
        
        if not success:
            terminal_status = mt5_manager.get_terminal_status()
            error_msg = "Unknown error"
            for status in terminal_status:
                if status["login"] == trader.login:
                    error_msg = status["error"]
                    break
            
            raise HTTPException(
                status_code=400,
                detail=f"Failed to configure {trader.label}: {error_msg}"
            )
        
        # Encode password for storage
        encoded_password = base64.b64encode(trader.password.encode()).decode()
        configured_traders.append({
            "login": trader.login,
            "password": encoded_password,
            "server": trader.server,
            "label": trader.label,
            "terminal_path": terminal_path
        })
    
    # Save configuration
    cache_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", ".cache"))
    os.makedirs(cache_dir, exist_ok=True)
    
    config_file = os.path.join(cache_dir, "traders_config.json")
    with open(config_file, "w") as f:
        json.dump({"traders": configured_traders}, f, indent=2)
    
    # Start polling with the new configuration
    mt5_manager.start_polling(configured_traders, interval=5)
    
    return {
        "status": "success",
        "message": f"Configured {len(configured_traders)} traders successfully",
        "traders": [{"login": t["login"], "label": t["label"]} for t in configured_traders]
    }

@router.get("/api/mt5/account-data/{login}")
async def get_account_data(login: str):
    """Get cached account data for a specific login"""
    data = get_account(login)
    if not data:
        raise HTTPException(status_code=404, detail="Account data not found")
    return data

@router.post("/api/mt5/refresh-data/{login}")
async def refresh_account_data(login: str, x_api_key: str = Header(None)):
    """Manually refresh data for a specific account"""
    
    # Load current configuration to get password
    cache_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", ".cache"))
    config_file = os.path.join(cache_dir, "traders_config.json")
    
    if not os.path.exists(config_file):
        raise HTTPException(status_code=400, detail="No trader configuration found")
    
    with open(config_file, "r") as f:
        config = json.load(f)
    
    # Find the trader
    trader = None
    for t in config["traders"]:
        if t["login"] == login:
            trader = t
            break
    
    if not trader:
        raise HTTPException(status_code=404, detail="Trader not found in configuration")
    
    # Decode password and collect data
    password = base64.b64decode(trader["password"]).decode()
    data = mt5_manager.collect_data_for_terminal(login, password)
    
    if data:
        return {"status": "success", "data": data}
    else:
        # Get error message
        status = mt5_manager.get_terminal_status()
        error_msg = "Unknown error"
        for s in status:
            if s["login"] == login:
                error_msg = s["error"]
                break
        
        raise HTTPException(status_code=500, detail=f"Failed to refresh data: {error_msg}")

@router.get("/api/mt5/chart-history/{symbol}")
async def get_chart_history(symbol: str, hours: int = 24, max_points: int = 180, smoothing: int = 0):
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
        
        # Apply smoothing if requested
        if smoothing > 0 and len(data) > smoothing:
            smoothed_data = []
            for i in range(len(data)):
                if i < smoothing:
                    # For early points, use available data
                    window_start = 0
                    window_end = i + 1
                else:
                    # Use moving average window
                    window_start = i - smoothing + 1
                    window_end = i + 1
                
                # Calculate moving average price
                window_prices = [data[j][1] for j in range(window_start, window_end)]
                avg_price = sum(window_prices) / len(window_prices)
                smoothed_data.append((data[i][0], avg_price))  # Keep original timestamp
            
            data = smoothed_data
        
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