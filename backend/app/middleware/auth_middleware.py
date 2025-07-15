"""
Authentication Middleware for WidgetForge
"""
from fastapi import Request, Response, HTTPException
from fastapi.responses import JSONResponse, RedirectResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp
import logging

from app.models.auth_models import auth_db

logger = logging.getLogger(__name__)

class AuthMiddleware(BaseHTTPMiddleware):
    def __init__(self, app: ASGIApp):
        super().__init__(app)
        
        # Routes that don't require authentication
        self.public_routes = {
            "/",
            "/ping",
            "/api/auth/login",
            "/admin/login",
            "/price/",  # Price data endpoints
            "/ws/price-stream",  # WebSocket price streaming
            "/api/rss/",  # RSS feeds
            "/api/forex-factory/",  # Forex factory data
            "/static/",  # Static files
            "/widgets/",  # Widget endpoints (public)
        }
        
        # Routes that require admin role
        self.admin_routes = {
            "/admin/",
            "/api/users",
            "/api/auth/reset-password",
        }
        
        # API routes that require authentication
        self.auth_routes = {
            "/api/auth/current-user",
            "/api/auth/change-password",
            "/api/auth/logout",
            "/api/accounts",
        }

    async def dispatch(self, request: Request, call_next):
        path = request.url.path
        
        # Check if route is public
        if self.is_public_route(path):
            return await call_next(request)
        
        # Get user from session
        session_token = request.cookies.get("session_token")
        user = None
        
        if session_token:
            # Clean up expired sessions
            auth_db.cleanup_expired_sessions()
            user = auth_db.get_session_user(session_token)
        
        # Check if route requires authentication
        if self.requires_auth(path):
            if not user:
                if path.startswith("/api/"):
                    return JSONResponse(
                        {"detail": "Authentication required"}, 
                        status_code=401
                    )
                else:
                    return RedirectResponse(url="/admin/login")
            
            # Check if route requires admin role
            if self.requires_admin(path) and user.role != "admin":
                if path.startswith("/api/"):
                    return JSONResponse(
                        {"detail": "Admin access required"}, 
                        status_code=403
                    )
                else:
                    return RedirectResponse(url="/admin/login")
        
        # Add user to request state
        request.state.user = user
        
        return await call_next(request)
    
    def is_public_route(self, path: str) -> bool:
        """Check if route is public"""
        return any(path.startswith(route) for route in self.public_routes)
    
    def requires_auth(self, path: str) -> bool:
        """Check if route requires authentication"""
        return (
            any(path.startswith(route) for route in self.auth_routes) or
            any(path.startswith(route) for route in self.admin_routes)
        )
    
    def requires_admin(self, path: str) -> bool:
        """Check if route requires admin role"""
        return any(path.startswith(route) for route in self.admin_routes)