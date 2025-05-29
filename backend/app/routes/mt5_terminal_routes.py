"""
MT5 Terminal Management API Routes - Production Version
"""
from fastapi import APIRouter, HTTPException, Header, Request, Query
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import List, Optional
import json
import os
from app.services.mt5_terminal_manager import mt5_terminal_manager

router = APIRouter()

class TerminalConfigRequest(BaseModel):
    terminal_id: int
    login: str
    password: str
    server: str
    label: str

class ConnectionTestRequest(BaseModel):
    login: str
    password: str
    server: str

@router.get("/api/mt5/available-terminals")
async def get_available_terminals():
    """Get list of available MT5 terminal slots"""
    available = mt5_terminal_manager.get_available_terminals()
    return {"available_terminals": available}

@router.get("/api/mt5/terminal-status")
async def get_terminal_status():
    """Get status of all configured terminals"""
    status = mt5_terminal_manager.get_terminal_status()
    return {"terminals": status}

@router.post("/api/mt5/test-connection")
async def test_connection(request: ConnectionTestRequest, x_api_key: str = Header(None)):
    """Test MT5 connection without saving configuration"""
    
    success, message = mt5_terminal_manager.test_connection(
        login=request.login,
        password=request.password,
        server=request.server
    )
    
    if success:
        return {"status": "success", "message": message}
    else:
        raise HTTPException(status_code=400, detail=message)

@router.post("/api/mt5/add-terminal")
async def add_terminal(request: TerminalConfigRequest, x_api_key: str = Header(None)):
    """Add a new terminal configuration"""
    
    success, message = mt5_terminal_manager.add_terminal(
        terminal_id=request.terminal_id,
        login=request.login,
        password=request.password,
        server=request.server,
        label=request.label
    )
    
    if success:
        return {"status": "success", "message": message}
    else:
        raise HTTPException(status_code=400, detail=message)

@router.post("/api/mt5/connect-terminal/{terminal_id}")
async def connect_terminal(terminal_id: int, x_api_key: str = Header(None)):
    """Connect (activate) a specific terminal"""
    
    success, message = mt5_terminal_manager.connect_terminal(terminal_id)
    
    if success:
        return {"status": "success", "message": message}
    else:
        raise HTTPException(status_code=400, detail=message)

@router.post("/api/mt5/disconnect-terminal/{terminal_id}")
async def disconnect_terminal(terminal_id: int, x_api_key: str = Header(None)):
    """Disconnect (deactivate) a specific terminal"""
    
    success, message = mt5_terminal_manager.disconnect_terminal(terminal_id)
    
    if success:
        return {"status": "success", "message": message}
    else:
        raise HTTPException(status_code=400, detail=message)

@router.delete("/api/mt5/remove-terminal/{terminal_id}")
async def remove_terminal(terminal_id: int, x_api_key: str = Header(None)):
    """Remove a terminal configuration completely"""
    
    success, message = mt5_terminal_manager.remove_terminal(terminal_id)
    
    if success:
        return {"status": "success", "message": message}
    else:
        raise HTTPException(status_code=400, detail=message)

@router.get("/api/mt5/terminal-data/{terminal_id}")
async def get_terminal_data(terminal_id: int):
    """Get cached data for a specific terminal"""
    
    data = mt5_terminal_manager.get_terminal_data(terminal_id)
    
    if data:
        return data
    else:
        raise HTTPException(status_code=404, detail="Terminal data not found")

@router.get("/api/mt5/active-terminals")
async def get_active_terminals():
    """Get list of active terminals for widget configuration"""
    
    active = mt5_terminal_manager.get_active_terminals()
    return {"active_terminals": active}

@router.get("/api/mt5/daily-stats/{terminal_id}")
async def get_daily_stats(terminal_id: int, date: Optional[str] = Query(None)):
    """Get daily trading statistics for a terminal"""
    
    stats = mt5_terminal_manager.get_daily_stats(terminal_id, date)
    
    if stats:
        return stats
    else:
        raise HTTPException(status_code=404, detail="Daily stats not found")

@router.get("/api/mt5/multi-terminal-data")
async def get_multi_terminal_data(terminal_ids: str = Query(..., description="Comma-separated terminal IDs")):
    """Get data for multiple terminals at once (for competition widgets)"""
    
    try:
        terminal_list = [int(tid.strip()) for tid in terminal_ids.split(',')]
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid terminal IDs format")
    
    results = {}
    for terminal_id in terminal_list:
        data = mt5_terminal_manager.get_terminal_data(terminal_id)
        if data:
            results[str(terminal_id)] = data
        else:
            results[str(terminal_id)] = None
    
    return {"terminals": results}

@router.get("/api/mt5/leaderboard")
async def get_leaderboard(sort_by: str = Query("profit", description="Sort by: profit, balance, equity, win_rate")):
    """Get leaderboard data for active terminals"""
    
    active_terminals = mt5_terminal_manager.get_active_terminals()
    leaderboard_data = []
    
    for terminal_info in active_terminals:
        terminal_id = terminal_info['terminal_id']
        data = mt5_terminal_manager.get_terminal_data(terminal_id)
        
        if data:
            leaderboard_entry = {
                'terminal_id': terminal_id,
                'label': data['label'],
                'balance': data['balance'],
                'equity': data['equity'],
                'profit': data['profit'],
                'trade_count': data['trade_count'],
                'daily_stats': data.get('daily_stats', {})
            }
            leaderboard_data.append(leaderboard_entry)
    
    # Sort the leaderboard
    if sort_by == "profit":
        leaderboard_data.sort(key=lambda x: x['profit'], reverse=True)
    elif sort_by == "balance":
        leaderboard_data.sort(key=lambda x: x['balance'], reverse=True)
    elif sort_by == "equity":
        leaderboard_data.sort(key=lambda x: x['equity'], reverse=True)
    elif sort_by == "win_rate":
        leaderboard_data.sort(key=lambda x: x['daily_stats'].get('win_rate', 0), reverse=True)
    
    return {"leaderboard": leaderboard_data, "sorted_by": sort_by}