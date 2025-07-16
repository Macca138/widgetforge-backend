"""
Authentication Routes for WidgetForge
"""
from fastapi import APIRouter, HTTPException, Request, Response, Depends, Cookie
from fastapi.responses import JSONResponse
from pydantic import BaseModel, EmailStr
from typing import Optional, List
from datetime import datetime
import logging

from app.models.auth_models import auth_db, User, TraderAccount

logger = logging.getLogger(__name__)

router = APIRouter()

# Request/Response Models
class LoginRequest(BaseModel):
    email: EmailStr
    password: str

class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str

class CreateUserRequest(BaseModel):
    email: EmailStr
    name: str
    password: str
    role: str = "trader"

class CreateAccountRequest(BaseModel):
    account_number: str
    investor_password: str
    label: str = ""

class UserResponse(BaseModel):
    id: int
    email: str
    name: str
    role: str
    must_change_password: bool
    created_at: Optional[datetime]
    last_login: Optional[datetime]

class AccountResponse(BaseModel):
    id: int
    account_number: str
    label: str
    is_active: bool
    created_at: Optional[datetime]
    last_tested: Optional[datetime]
    connection_status: str
    last_error_message: Optional[str]

# Authentication Dependency
def get_current_user(session_token: Optional[str] = Cookie(None)) -> Optional[User]:
    """Get current user from session cookie"""
    if not session_token:
        return None
    
    # Clean up expired sessions
    auth_db.cleanup_expired_sessions()
    
    # Get user from session
    user = auth_db.get_session_user(session_token)
    return user

def require_auth(user: User = Depends(get_current_user)) -> User:
    """Require authentication"""
    if not user:
        raise HTTPException(status_code=401, detail="Authentication required")
    return user

def require_admin(user: User = Depends(require_auth)) -> User:
    """Require admin role"""
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    return user

# Authentication Endpoints
@router.post("/api/auth/login")
async def login(request: LoginRequest, response: Response):
    """User login"""
    try:
        # Get user by email
        user = auth_db.get_user_by_email(request.email)
        if not user:
            raise HTTPException(status_code=401, detail="Invalid credentials")
        
        # Verify password
        if not auth_db.verify_password(request.password, user.password_hash):
            raise HTTPException(status_code=401, detail="Invalid credentials")
        
        # Create session
        session_token = auth_db.create_session(user.id)
        
        # Update last login
        auth_db.update_last_login(user.id)
        
        # Set secure cookie
        response.set_cookie(
            key="session_token",
            value=session_token,
            httponly=True,
            secure=True,
            samesite="lax",
            max_age=24 * 60 * 60  # 24 hours
        )
        
        return {
            "status": "success",
            "user": UserResponse(
                id=user.id,
                email=user.email,
                name=user.name,
                role=user.role,
                must_change_password=user.must_change_password,
                created_at=user.created_at,
                last_login=user.last_login
            )
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Login error: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.post("/api/auth/logout")
async def logout(response: Response, session_token: Optional[str] = Cookie(None)):
    """User logout"""
    if session_token:
        auth_db.delete_session(session_token)
    
    # Clear cookie
    response.delete_cookie("session_token")
    
    return {"status": "success", "message": "Logged out successfully"}

@router.get("/api/auth/current-user")
async def get_current_user_info(user: User = Depends(require_auth)):
    """Get current user information"""
    return UserResponse(
        id=user.id,
        email=user.email,
        name=user.name,
        role=user.role,
        must_change_password=user.must_change_password,
        created_at=user.created_at,
        last_login=user.last_login
    )

@router.post("/api/auth/change-password")
async def change_password(request: ChangePasswordRequest, user: User = Depends(require_auth)):
    """Change user password"""
    try:
        # Verify current password
        if not auth_db.verify_password(request.current_password, user.password_hash):
            raise HTTPException(status_code=400, detail="Current password is incorrect")
        
        # Update password
        if auth_db.update_user_password(user.id, request.new_password):
            return {"status": "success", "message": "Password changed successfully"}
        else:
            raise HTTPException(status_code=500, detail="Failed to update password")
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Password change error: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

# User Management (Admin Only)
@router.get("/api/users")
async def get_all_users(admin: User = Depends(require_admin)):
    """Get all users (admin only)"""
    users = auth_db.get_all_users()
    return [UserResponse(
        id=user.id,
        email=user.email,
        name=user.name,
        role=user.role,
        must_change_password=user.must_change_password,
        created_at=user.created_at,
        last_login=user.last_login
    ) for user in users]

@router.post("/api/users")
async def create_user(request: CreateUserRequest, admin: User = Depends(require_admin)):
    """Create new user (admin only)"""
    try:
        # Validate role
        if request.role not in ["trader", "admin"]:
            raise HTTPException(status_code=400, detail="Invalid role")
        
        # Create user
        user = auth_db.create_user(
            email=request.email,
            name=request.name,
            password=request.password,
            role=request.role,
            created_by_admin_id=admin.id
        )
        
        if user:
            return {
                "status": "success",
                "user": UserResponse(
                    id=user.id,
                    email=user.email,
                    name=user.name,
                    role=user.role,
                    must_change_password=user.must_change_password,
                    created_at=user.created_at,
                    last_login=user.last_login
                ),
                "temporary_password": request.password
            }
        else:
            raise HTTPException(status_code=400, detail="User already exists")
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"User creation error: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.post("/api/users/{user_id}/reset-password")
async def reset_user_password(user_id: int, admin: User = Depends(require_admin)):
    """Reset user password (admin only)"""
    try:
        # Generate temporary password
        import secrets
        temp_password = secrets.token_urlsafe(12)
        
        # Update password
        if auth_db.update_user_password(user_id, temp_password):
            # Mark password as must change
            with auth_db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    'UPDATE users SET must_change_password = TRUE WHERE id = ?',
                    (user_id,)
                )
                conn.commit()
            
            return {
                "status": "success",
                "message": "Password reset successfully",
                "temporary_password": temp_password
            }
        else:
            raise HTTPException(status_code=404, detail="User not found")
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Password reset error: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

# Account Management
@router.get("/api/accounts")
async def get_accounts(user: User = Depends(require_auth)):
    """Get accounts (own for traders, all for admins)"""
    if user.role == "admin":
        # Admin sees all accounts with user info
        accounts = auth_db.get_all_accounts()
        return [
            {
                "id": account["id"],
                "account_number": account["account_number"],
                "label": account["label"],
                "is_active": account["is_active"],
                "created_at": account["created_at"],
                "last_tested": account["last_tested"],
                "connection_status": account["connection_status"],
                "last_error_message": account["last_error_message"],
                "user_name": account["user_name"],
                "user_email": account["user_email"]
            }
            for account in accounts
        ]
    else:
        # Trader sees only their own accounts
        accounts = auth_db.get_user_accounts(user.id)
        return [AccountResponse(
            id=account.id,
            account_number=account.account_number,
            label=account.label,
            is_active=account.is_active,
            created_at=account.created_at,
            last_tested=account.last_tested,
            connection_status=account.connection_status,
            last_error_message=account.last_error_message
        ) for account in accounts]

@router.post("/api/accounts")
async def create_account(request: CreateAccountRequest, user: User = Depends(require_auth)):
    """Create new trading account"""
    try:
        account = auth_db.create_trader_account(
            user_id=user.id,
            account_number=request.account_number,
            investor_password=request.investor_password,
            label=request.label
        )
        
        if account:
            return {
                "status": "success",
                "account": AccountResponse(
                    id=account.id,
                    account_number=account.account_number,
                    label=account.label,
                    is_active=account.is_active,
                    created_at=account.created_at,
                    last_tested=account.last_tested,
                    connection_status=account.connection_status,
                    last_error_message=account.last_error_message
                )
            }
        else:
            raise HTTPException(status_code=400, detail="Account already exists")
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Account creation error: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.post("/api/accounts/{account_id}/test-connection")
async def test_account_connection(account_id: int, user: User = Depends(require_auth)):
    """Test account connection to 5ers API"""
    try:
        # Get account (must belong to user unless admin)
        if user.role == "admin":
            accounts = auth_db.get_all_accounts()
            account = next((a for a in accounts if a["id"] == account_id), None)
        else:
            user_accounts = auth_db.get_user_accounts(user.id)
            account = next((a for a in user_accounts if a.id == account_id), None)
        
        if not account:
            raise HTTPException(status_code=404, detail="Account not found")
        
        # TODO: Implement actual 5ers API connection test
        # For now, simulate success
        auth_db.update_account_status(account_id, "connected", None)
        
        return {
            "status": "success",
            "message": "Connection test successful",
            "connection_status": "connected"
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Connection test error: {str(e)}")
        auth_db.update_account_status(account_id, "error", str(e))
        raise HTTPException(status_code=500, detail="Connection test failed")

@router.delete("/api/accounts/{account_id}")
async def delete_account(account_id: int, user: User = Depends(require_auth)):
    """Delete trading account"""
    try:
        # Check if account belongs to user (unless admin)
        if user.role != "admin":
            user_accounts = auth_db.get_user_accounts(user.id)
            if not any(a.id == account_id for a in user_accounts):
                raise HTTPException(status_code=404, detail="Account not found")
        
        # Soft delete (mark as inactive)
        with auth_db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                'UPDATE trader_accounts SET is_active = FALSE WHERE id = ?',
                (account_id,)
            )
            conn.commit()
            
            if cursor.rowcount > 0:
                return {"status": "success", "message": "Account deleted successfully"}
            else:
                raise HTTPException(status_code=404, detail="Account not found")
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Account deletion error: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")