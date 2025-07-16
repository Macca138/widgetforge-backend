"""
Authentication Models for WidgetForge
"""
import sqlite3
import os
import hashlib
import secrets
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Tuple
from dataclasses import dataclass
from cryptography.fernet import Fernet

@dataclass
class User:
    id: Optional[int] = None
    email: str = ""
    name: str = ""
    password_hash: str = ""
    role: str = "trader"  # trader or admin
    must_change_password: bool = True
    created_at: Optional[datetime] = None
    last_login: Optional[datetime] = None
    created_by_admin_id: Optional[int] = None

@dataclass
class TraderAccount:
    id: Optional[int] = None
    user_id: int = 0
    account_number: str = ""
    encrypted_investor_password: str = ""
    label: str = ""
    is_active: bool = True
    created_at: Optional[datetime] = None
    last_tested: Optional[datetime] = None
    connection_status: str = "disconnected"  # connected, disconnected, error
    last_error_message: Optional[str] = None

@dataclass
class UserSession:
    id: Optional[int] = None
    user_id: int = 0
    session_token: str = ""
    expires_at: datetime = None
    created_at: Optional[datetime] = None

class AuthDatabase:
    def __init__(self, db_path: str = None):
        if db_path is None:
            # Use .cache directory for database
            cache_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", ".cache"))
            os.makedirs(cache_dir, exist_ok=True)
            db_path = os.path.join(cache_dir, "auth.db")
        
        self.db_path = db_path
        self.init_encryption()
        self.init_database()
    
    def init_encryption(self):
        """Initialize encryption for investor passwords"""
        cache_dir = os.path.dirname(self.db_path)
        key_file = os.path.join(cache_dir, "auth_key.key")
        
        if os.path.exists(key_file):
            with open(key_file, 'rb') as f:
                self.encryption_key = f.read()
        else:
            self.encryption_key = Fernet.generate_key()
            with open(key_file, 'wb') as f:
                f.write(self.encryption_key)
        
        self.cipher = Fernet(self.encryption_key)
    
    def encrypt_password(self, password: str) -> str:
        """Encrypt investor password for secure storage"""
        return self.cipher.encrypt(password.encode()).decode()
    
    def decrypt_password(self, encrypted_password: str) -> str:
        """Decrypt investor password for use"""
        return self.cipher.decrypt(encrypted_password.encode()).decode()
    
    def init_database(self):
        """Initialize database tables"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    email TEXT UNIQUE NOT NULL,
                    name TEXT NOT NULL,
                    password_hash TEXT NOT NULL,
                    role TEXT NOT NULL DEFAULT 'trader',
                    must_change_password BOOLEAN DEFAULT TRUE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_login TIMESTAMP,
                    created_by_admin_id INTEGER REFERENCES users(id)
                )
            ''')
            
            conn.execute('''
                CREATE TABLE IF NOT EXISTS trader_accounts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    account_number TEXT NOT NULL,
                    encrypted_investor_password TEXT NOT NULL,
                    label TEXT,
                    is_active BOOLEAN DEFAULT TRUE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_tested TIMESTAMP,
                    connection_status TEXT DEFAULT 'disconnected',
                    last_error_message TEXT,
                    FOREIGN KEY (user_id) REFERENCES users (id)
                )
            ''')
            
            conn.execute('''
                CREATE TABLE IF NOT EXISTS user_sessions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    session_token TEXT UNIQUE NOT NULL,
                    expires_at TIMESTAMP NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users (id)
                )
            ''')
            
            conn.commit()
    
    def hash_password(self, password: str) -> str:
        """Hash password using SHA-256 with salt"""
        salt = secrets.token_hex(32)
        password_hash = hashlib.sha256((password + salt).encode()).hexdigest()
        return f"{salt}${password_hash}"
    
    def verify_password(self, password: str, password_hash: str) -> bool:
        """Verify password against hash"""
        try:
            salt, hash_value = password_hash.split('$')
            return hashlib.sha256((password + salt).encode()).hexdigest() == hash_value
        except:
            return False
    
    def generate_session_token(self) -> str:
        """Generate secure session token"""
        return secrets.token_urlsafe(32)
    
    # User Management
    def create_user(self, email: str, name: str, password: str, role: str = "trader", 
                   created_by_admin_id: Optional[int] = None) -> Optional[User]:
        """Create a new user"""
        try:
            password_hash = self.hash_password(password)
            
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO users (email, name, password_hash, role, created_by_admin_id)
                    VALUES (?, ?, ?, ?, ?)
                ''', (email, name, password_hash, role, created_by_admin_id))
                
                user_id = cursor.lastrowid
                conn.commit()
                
                return User(
                    id=user_id,
                    email=email,
                    name=name,
                    password_hash=password_hash,
                    role=role,
                    created_by_admin_id=created_by_admin_id,
                    created_at=datetime.now()
                )
        except sqlite3.IntegrityError:
            return None  # User already exists
    
    def get_user_by_email(self, email: str) -> Optional[User]:
        """Get user by email"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM users WHERE email = ?', (email,))
            row = cursor.fetchone()
            
            if row:
                return User(
                    id=row[0],
                    email=row[1],
                    name=row[2],
                    password_hash=row[3],
                    role=row[4],
                    must_change_password=bool(row[5]),
                    created_at=datetime.fromisoformat(row[6]) if row[6] else None,
                    last_login=datetime.fromisoformat(row[7]) if row[7] else None,
                    created_by_admin_id=row[8]
                )
        return None
    
    def get_user_by_id(self, user_id: int) -> Optional[User]:
        """Get user by ID"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM users WHERE id = ?', (user_id,))
            row = cursor.fetchone()
            
            if row:
                return User(
                    id=row[0],
                    email=row[1],
                    name=row[2],
                    password_hash=row[3],
                    role=row[4],
                    must_change_password=bool(row[5]),
                    created_at=datetime.fromisoformat(row[6]) if row[6] else None,
                    last_login=datetime.fromisoformat(row[7]) if row[7] else None,
                    created_by_admin_id=row[8]
                )
        return None
    
    def update_user_password(self, user_id: int, new_password: str) -> bool:
        """Update user password"""
        try:
            password_hash = self.hash_password(new_password)
            
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    UPDATE users 
                    SET password_hash = ?, must_change_password = FALSE
                    WHERE id = ?
                ''', (password_hash, user_id))
                
                conn.commit()
                return cursor.rowcount > 0
        except:
            return False
    
    def update_last_login(self, user_id: int) -> bool:
        """Update user's last login time"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    UPDATE users 
                    SET last_login = CURRENT_TIMESTAMP
                    WHERE id = ?
                ''', (user_id,))
                
                conn.commit()
                return cursor.rowcount > 0
        except:
            return False
    
    def get_all_users(self) -> List[User]:
        """Get all users (admin only)"""
        users = []
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM users ORDER BY created_at DESC')
            rows = cursor.fetchall()
            
            for row in rows:
                users.append(User(
                    id=row[0],
                    email=row[1],
                    name=row[2],
                    password_hash=row[3],
                    role=row[4],
                    must_change_password=bool(row[5]),
                    created_at=datetime.fromisoformat(row[6]) if row[6] else None,
                    last_login=datetime.fromisoformat(row[7]) if row[7] else None,
                    created_by_admin_id=row[8]
                ))
        return users
    
    # Session Management
    def create_session(self, user_id: int, expires_hours: int = 24) -> str:
        """Create a new user session"""
        session_token = self.generate_session_token()
        expires_at = datetime.now() + timedelta(hours=expires_hours)
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO user_sessions (user_id, session_token, expires_at)
                VALUES (?, ?, ?)
            ''', (user_id, session_token, expires_at))
            conn.commit()
        
        return session_token
    
    def get_session_user(self, session_token: str) -> Optional[User]:
        """Get user from session token"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT u.* FROM users u
                JOIN user_sessions s ON u.id = s.user_id
                WHERE s.session_token = ? AND s.expires_at > CURRENT_TIMESTAMP
            ''', (session_token,))
            row = cursor.fetchone()
            
            if row:
                return User(
                    id=row[0],
                    email=row[1],
                    name=row[2],
                    password_hash=row[3],
                    role=row[4],
                    must_change_password=bool(row[5]),
                    created_at=datetime.fromisoformat(row[6]) if row[6] else None,
                    last_login=datetime.fromisoformat(row[7]) if row[7] else None,
                    created_by_admin_id=row[8]
                )
        return None
    
    def delete_session(self, session_token: str) -> bool:
        """Delete a session (logout)"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('DELETE FROM user_sessions WHERE session_token = ?', (session_token,))
                conn.commit()
                return cursor.rowcount > 0
        except:
            return False
    
    def cleanup_expired_sessions(self):
        """Clean up expired sessions"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('DELETE FROM user_sessions WHERE expires_at < CURRENT_TIMESTAMP')
            conn.commit()
    
    # Trader Account Management
    def create_trader_account(self, user_id: int, account_number: str, 
                            investor_password: str, label: str = "") -> Optional[TraderAccount]:
        """Create a new trader account"""
        try:
            encrypted_password = self.encrypt_password(investor_password)
            
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO trader_accounts (user_id, account_number, encrypted_investor_password, label)
                    VALUES (?, ?, ?, ?)
                ''', (user_id, account_number, encrypted_password, label))
                
                account_id = cursor.lastrowid
                conn.commit()
                
                return TraderAccount(
                    id=account_id,
                    user_id=user_id,
                    account_number=account_number,
                    encrypted_investor_password=encrypted_password,
                    label=label,
                    created_at=datetime.now()
                )
        except sqlite3.IntegrityError:
            return None
    
    def get_user_accounts(self, user_id: int) -> List[TraderAccount]:
        """Get all accounts for a user"""
        accounts = []
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT * FROM trader_accounts 
                WHERE user_id = ? AND is_active = TRUE
                ORDER BY created_at DESC
            ''', (user_id,))
            rows = cursor.fetchall()
            
            for row in rows:
                accounts.append(TraderAccount(
                    id=row[0],
                    user_id=row[1],
                    account_number=row[2],
                    encrypted_investor_password=row[3],
                    label=row[4],
                    is_active=bool(row[5]),
                    created_at=datetime.fromisoformat(row[6]) if row[6] else None,
                    last_tested=datetime.fromisoformat(row[7]) if row[7] else None,
                    connection_status=row[8],
                    last_error_message=row[9]
                ))
        return accounts
    
    def get_all_accounts(self) -> List[Dict]:
        """Get all accounts with user info (admin only)"""
        accounts = []
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT ta.*, u.name, u.email 
                FROM trader_accounts ta
                JOIN users u ON ta.user_id = u.id
                WHERE ta.is_active = TRUE
                ORDER BY u.name, ta.created_at DESC
            ''')
            rows = cursor.fetchall()
            
            for row in rows:
                accounts.append({
                    'id': row[0],
                    'user_id': row[1],
                    'account_number': row[2],
                    'encrypted_investor_password': row[3],
                    'label': row[4],
                    'is_active': bool(row[5]),
                    'created_at': datetime.fromisoformat(row[6]) if row[6] else None,
                    'last_tested': datetime.fromisoformat(row[7]) if row[7] else None,
                    'connection_status': row[8],
                    'last_error_message': row[9],
                    'user_name': row[10],
                    'user_email': row[11]
                })
        return accounts
    
    def update_account_status(self, account_id: int, status: str, error_message: str = None) -> bool:
        """Update account connection status"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    UPDATE trader_accounts 
                    SET connection_status = ?, last_error_message = ?, last_tested = CURRENT_TIMESTAMP
                    WHERE id = ?
                ''', (status, error_message, account_id))
                
                conn.commit()
                return cursor.rowcount > 0
        except:
            return False
    
    def get_connection(self):
        """Get database connection (for context manager)"""
        return sqlite3.connect(self.db_path)

# Global database instance
auth_db = AuthDatabase()