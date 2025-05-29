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