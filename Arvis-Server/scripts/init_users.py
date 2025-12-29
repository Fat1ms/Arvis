"""
Initial Users Setup Script
Скрипт начальной настройки пользователей
"""

import hashlib
import secrets
import sys
import uuid
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from server.config import get_settings
from server.database.models import RoleEnum, User
from server.database.storage import DatabaseStorage, SessionLocal, init_database

settings = get_settings()


def create_demo_users():
    """Create demo users for testing and demonstration"""
    
    print("=" * 60)
    print("🤖 Arvis Authentication Server - Initial Users Setup")
    print("=" * 60)
    print()
    
    # Initialize database
    init_database()
    db = SessionLocal()
    storage = DatabaseStorage(db)
    
    users_to_create = [
        {
            "username": "admin",
            "password": settings.admin_password,
            "email": "admin@arvis.local",
            "role": RoleEnum.ADMIN,
            "require_2fa": False,
            "description": "Администратор системы - полный доступ"
        },
        {
            "username": "user",
            "password": "UserPass123!",
            "email": "user@arvis.local",
            "role": RoleEnum.USER,
            "require_2fa": False,
            "description": "Обычный пользователь - доступ ко всем модулям"
        },
        {
            "username": "poweruser",
            "password": "PowerUser123!",
            "email": "poweruser@arvis.local",
            "role": RoleEnum.POWER_USER,
            "require_2fa": False,
            "description": "Продвинутый пользователь - выполнение кода и скриптов"
        },
        {
            "username": "guest",
            "password": "GuestPass123!",
            "email": "guest@arvis.local",
            "role": RoleEnum.GUEST,
            "require_2fa": False,
            "description": "Гость - только чат и базовые модули (30 мин сессия)"
        }
    ]
    
    created_users = []
    
    for user_data in users_to_create:
        # Check if user already exists
        existing_user = storage.get_user_by_username(user_data["username"])
        
        if existing_user:
            print(f"⚠️  Пользователь '{user_data['username']}' уже существует, пропускаем...")
            continue
        
        # Create user
        salt = secrets.token_hex(32)
        password_hash = hashlib.sha256(
            (user_data["password"] + salt).encode()
        ).hexdigest()
        
        user = User(
            user_id=str(uuid.uuid4()),
            username=user_data["username"],
            email=user_data["email"],
            password_hash=password_hash,
            salt=salt,
            role=user_data["role"],
            is_active=True,
            require_2fa=user_data["require_2fa"]
        )
        
        storage.create_user(user)
        created_users.append(user_data)
        print(f"✅ Создан: {user_data['username']:12} | {user_data['role'].value:12} | {user_data['description']}")
    
    db.close()
    
    if created_users:
        print()
        print("=" * 60)
        print("📋 Созданные учётные записи:")
        print("=" * 60)
        for user_data in created_users:
            print(f"\n👤 {user_data['username'].upper()}")
            print(f"   Логин:    {user_data['username']}")
            print(f"   Пароль:   {user_data['password']}")
            print(f"   Роль:     {user_data['role'].value}")
            print(f"   Описание: {user_data['description']}")
        
        print()
        print("=" * 60)
        print("⚠️  ВАЖНО: Сохраните эти пароли в безопасном месте!")
        print("⚠️  Рекомендуется сменить пароли после первого входа!")
        print("=" * 60)
    else:
        print()
        print("ℹ️  Все пользователи уже существуют.")
    
    print()
    print("✅ Инициализация завершена!")
    return created_users


if __name__ == "__main__":
    create_demo_users()
