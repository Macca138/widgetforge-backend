#!/usr/bin/env python3
"""
Initialize Authentication Database
Creates the first admin user for WidgetForge
"""
import os
import sys
from pathlib import Path

# Add the app directory to Python path
sys.path.insert(0, str(Path(__file__).parent))

from app.models.auth_models import auth_db

def init_admin_user():
    """Create the first admin user"""
    print("🔧 Initializing WidgetForge Authentication Database...")
    
    # Check if admin user already exists
    existing_admin = auth_db.get_user_by_email("admin@widgetforge.com")
    if existing_admin:
        print("✅ Admin user already exists!")
        print(f"   Email: {existing_admin.email}")
        print(f"   Name: {existing_admin.name}")
        print(f"   Role: {existing_admin.role}")
        return
    
    # Create first admin user
    admin_password = "WidgetForge2024!"
    admin_user = auth_db.create_user(
        email="admin@widgetforge.com",
        name="System Administrator",
        password=admin_password,
        role="admin"
    )
    
    if admin_user:
        print("✅ Admin user created successfully!")
        print(f"   Email: {admin_user.email}")
        print(f"   Name: {admin_user.name}")
        print(f"   Role: {admin_user.role}")
        print(f"   Password: {admin_password}")
        print()
        print("🔐 Please change this password after first login!")
        print("   Login at: /admin/login")
    else:
        print("❌ Failed to create admin user")

if __name__ == "__main__":
    init_admin_user()