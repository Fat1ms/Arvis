"""
Reset Admin Password Script
Скрипт для сброса пароля администратора
"""

import sys
import bcrypt
import secrets
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from server.database.storage import SessionLocal, DatabaseStorage
from server.config import get_settings

settings = get_settings()


def reset_admin_password():
    """Reset admin user password with correct bcrypt hashing"""
    db = SessionLocal()
    try:
        storage = DatabaseStorage(db)
        
        # Get admin user
        admin = storage.get_user_by_username(settings.admin_username)
        
        if not admin:
            print(f"❌ Admin user '{settings.admin_username}' not found!")
            return False
        
        # Generate new password hash with bcrypt
        salt = secrets.token_hex(8)  # 8 bytes = 16 hex chars
        password = settings.admin_password
        
        # Bcrypt has 72 byte limit
        password_bytes = (password + salt).encode('utf-8')[:72]
        password_hash = bcrypt.hashpw(password_bytes, bcrypt.gensalt()).decode('utf-8')
        
        # Update admin user
        admin.password_hash = password_hash
        admin.salt = salt
        storage.update_user(admin)
        
        print(f"✓ Admin password reset successfully!")
        print(f"  Username: {settings.admin_username}")
        print(f"  Password: {settings.admin_password}")
        print(f"  Hash: {password_hash[:50]}...")
        print(f"  Salt: {salt}")
        print("\n⚠ Please change the admin password immediately after login!")
        
        return True
        
    except Exception as e:
        print(f"❌ Error resetting admin password: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        db.close()


if __name__ == "__main__":
    print("=" * 80)
    print("🔐 Arvis Authentication Server - Admin Password Reset")
    print("=" * 80)
    print()
    
    if reset_admin_password():
        print("\n✓ Password reset completed successfully!")
        sys.exit(0)
    else:
        print("\n❌ Password reset failed!")
        sys.exit(1)
