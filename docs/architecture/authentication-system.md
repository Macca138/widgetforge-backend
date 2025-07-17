# Authentication System Design - WidgetForge Backend

## Overview
Complete redesign of authentication system to support role-based access for traders and admins, with proper user management and account linking for 5ers API integration.

## System Architecture

### User Roles & Permissions

#### **Trader Role:**
- **Access**: Limited, account-specific
- **Capabilities**:
  - Input/update their own MT5 account details (account number, investor password)
  - View their own account status/connection
  - See their own data preview
  - Change their own password
- **Restrictions**:
  - Cannot see other traders' accounts
  - Cannot create widgets
  - Cannot access system settings
  - Cannot manage other users

#### **Admin Role:**
- **Access**: Full system access
- **Capabilities**:
  - All trader functions (can add their own accounts)
  - Create/manage user accounts
  - Select any accounts for widgets
  - Build and configure widgets
  - Manage system settings (API keys, endpoints)
  - View all account data
  - Access analytics/monitoring

### Authentication Flow

```
1. Admin creates user account (email + name + temp password)
2. Admin provides credentials to user (no email sending)
3. User visits /login, enters email + temp password
4. System forces password reset on first login
5. User redirected to role-specific dashboard:
   - Traders → /trader/dashboard
   - Admins → /admin/dashboard
```

### Database Schema

```sql
users (
  id SERIAL PRIMARY KEY,
  email VARCHAR(255) UNIQUE NOT NULL,
  name VARCHAR(255) NOT NULL,
  password_hash VARCHAR(255) NOT NULL,
  role ENUM('trader', 'admin') NOT NULL,
  must_change_password BOOLEAN DEFAULT TRUE,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  last_login TIMESTAMP,
  created_by_admin_id INTEGER REFERENCES users(id)
)

trader_accounts (
  id SERIAL PRIMARY KEY,
  user_id INTEGER REFERENCES users(id),
  account_number VARCHAR(50) NOT NULL,
  encrypted_investor_password TEXT NOT NULL,
  label VARCHAR(255),
  is_active BOOLEAN DEFAULT TRUE,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  last_tested TIMESTAMP,
  connection_status ENUM('connected', 'disconnected', 'error') DEFAULT 'disconnected',
  last_error_message TEXT
)

widget_configs (
  id SERIAL PRIMARY KEY,
  created_by_admin_id INTEGER REFERENCES users(id),
  name VARCHAR(255) NOT NULL,
  selected_accounts JSON NOT NULL,
  widget_settings JSON NOT NULL,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  last_used TIMESTAMP
)

user_sessions (
  id SERIAL PRIMARY KEY,
  user_id INTEGER REFERENCES users(id),
  session_token VARCHAR(255) UNIQUE NOT NULL,
  expires_at TIMESTAMP NOT NULL,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
```

### Key Features

#### **Account Auto-Assignment:**
- When trader logs in and adds account details
- Accounts automatically linked to their user ID
- No manual assignment needed

#### **Admin Account Selection:**
- Widget builder shows all active accounts
- Grouped by trader name (not email)
- Easy selection interface for daily streams

#### **Admin as Trader:**
- Admin role inherits all trader functions
- Can manage their own accounts
- Can select their own accounts in widgets

#### **User Name Display:**
- User's name field used in widget displays
- Makes it easy for producers to identify accounts
- Format: "John Smith - Main Account" instead of "trader@example.com - Account"

### UI Flow

#### **Trader Dashboard:**
```
┌─────────────────────────────────────┐
│ Welcome, John Smith                 │
│ (trader@example.com)                │
├─────────────────────────────────────┤
│ My Trading Accounts                 │
│ ┌─────────────────────────────────┐ │
│ │ Account #50012345               │ │
│ │ Label: Main Account             │ │
│ │ Status: ✅ Connected            │ │
│ │ [Edit] [Test] [Remove]          │ │
│ └─────────────────────────────────┘ │
│ [+ Add New Account]                 │
│                                     │
│ [Change Password] [Profile]         │
└─────────────────────────────────────┘
```

#### **Admin Dashboard:**
```
┌─────────────────────────────────────┐
│ Welcome, Producer Name              │
│ (admin@example.com)                 │
├─────────────────────────────────────┤
│ [My Accounts] [Widget Builder]      │
│ [User Management] [System Settings] │
│                                     │
│ Widget Builder - Select Accounts:   │
│ ☑ Producer Name - Main Account      │
│ ☑ John Smith - Account A            │
│ ☐ Jane Doe - Account B              │
│ [Generate Widget]                   │
└─────────────────────────────────────┘
```

#### **User Management (Admin Only):**
```
┌─────────────────────────────────────┐
│ User Management                     │
├─────────────────────────────────────┤
│ John Smith (trader@example.com)     │
│ Role: Trader | Last Login: 2 hrs ago│
│ Accounts: 1 | Status: Active       │
│ [Edit] [Reset Password] [Deactivate]│
│                                     │
│ [+ Add New User]                    │
└─────────────────────────────────────┘
```

### Security Implementation

#### **Password Security:**
- bcrypt hashing with salt
- Minimum password requirements
- Forced password change on first login
- Password change functionality

#### **Session Management:**
- Server-side sessions with database storage
- Session expiration (24 hours)
- Session invalidation on logout
- CSRF protection with tokens

#### **Role-Based Access:**
- Middleware to check user roles
- Route protection based on permissions
- API endpoint security
- Frontend route guards

#### **Data Encryption:**
- Investor passwords encrypted with Fernet
- Secure key management
- Database encryption at rest

### Implementation Phases

#### **Phase 1: Authentication System**
1. User management database setup
2. Login/logout functionality with sessions
3. Role-based routing and middleware
4. Password reset flow
5. User creation interface (admin only)

#### **Phase 2: Account Management**
1. Trader account input interface
2. Encrypted storage for investor passwords
3. 5ers API connection testing
4. Account status monitoring
5. Account management for traders

#### **Phase 3: Admin Features**
1. User creation and management interface
2. Account selection for widgets
3. Widget configuration with name display
4. System settings management

#### **Phase 4: Widget Integration**
1. Update widget builders to use new authentication
2. Account selection based on user names
3. Real-time account data display
4. Widget embedding with proper permissions

### API Endpoints

#### **Authentication:**
- `POST /api/auth/login`
- `POST /api/auth/logout`
- `POST /api/auth/change-password`
- `GET /api/auth/current-user`

#### **User Management (Admin):**
- `GET /api/users`
- `POST /api/users`
- `PUT /api/users/{id}`
- `DELETE /api/users/{id}`
- `POST /api/users/{id}/reset-password`

#### **Account Management:**
- `GET /api/accounts` (own accounts for traders, all for admins)
- `POST /api/accounts`
- `PUT /api/accounts/{id}`
- `DELETE /api/accounts/{id}`
- `POST /api/accounts/{id}/test-connection`

#### **Widget Configuration:**
- `GET /api/widgets`
- `POST /api/widgets`
- `PUT /api/widgets/{id}`
- `DELETE /api/widgets/{id}`
- `GET /api/widgets/{id}/accounts`

### Migration Plan

#### **From Current System:**
1. Backup current admin credentials
2. Create new database tables
3. Migrate existing MT5 account data (if any)
4. Update all frontend templates
5. Remove hardcoded authentication
6. Test thoroughly before deployment

#### **Deployment Strategy:**
1. Deploy authentication system first
2. Test with admin accounts
3. Add trader accounts gradually
4. Update widget system
5. Remove old authentication completely

### Security Considerations

#### **Data Protection:**
- All sensitive data encrypted
- Secure password storage
- Session security
- API rate limiting

#### **Access Control:**
- Role-based permissions
- User activity logging
- Failed login attempt tracking
- Session timeout enforcement

#### **Compliance:**
- No personal data beyond name/email
- Secure credential handling
- Audit trail for all actions
- Regular security reviews

---

**This design provides a secure, scalable authentication system that supports the workflow of traders providing account details and admins creating widgets for live streaming.**