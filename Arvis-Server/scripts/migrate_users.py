"""
Migrate users from local SQLite to authentication server
Миграция пользователей на сервер аутентификации
"""

import argparse
import sqlite3
import sys
from pathlib import Path

# Добавляем путь к проекту
sys.path.insert(0, str(Path(__file__).parent))

from utils.security.auth_client import AuthClient


def migrate_users(source_db: str, server_url: str, admin_username: str, admin_password: str):
    """Migrate users from local DB to server"""
    print("=" * 60)
    print("🔄 Arvis User Migration Tool")
    print("=" * 60)

    # Подключаемся к локальной БД
    print(f"📂 Reading from: {source_db}")
    conn = sqlite3.connect(source_db)
    cursor = conn.cursor()

    # Получаем всех пользователей
    cursor.execute(
        """
        SELECT user_id, username, role, password_hash, salt,
               created_at, last_login, is_active, require_2fa, totp_secret
        FROM users
    """
    )

    users = cursor.fetchall()
    print(f"👥 Found {len(users)} users to migrate")

    # Подключаемся к серверу
    print(f"🌐 Connecting to server: {server_url}")
    client = AuthClient(server_url)

    if not client.check_connection():
        print("❌ Server is not reachable!")
        return False

    # Логинимся как админ
    print(f"🔐 Logging in as admin: {admin_username}")
    if not client.login(admin_username, admin_password):
        print("❌ Admin login failed!")
        return False

    print("✅ Admin login successful")

    # Мигрируем пользователей
    migrated = 0
    skipped = 0

    for user in users:
        (
            user_id,
            username,
            role,
            password_hash,
            salt,
            created_at,
            last_login,
            is_active,
            require_2fa,
            totp_secret,
        ) = user

        # Пропускаем админа (он уже должен быть создан на сервере)
        if username == admin_username:
            print(f"⏭️  Skipping admin user: {username}")
            skipped += 1
            continue

        print(f"📤 Migrating user: {username} (role: {role})")

        # Создаём пользователя на сервере
        # NOTE: Для миграции нужен специальный API endpoint, который принимает хеши
        # Сейчас используем create_user с временным паролем

        # TODO: Implement proper migration endpoint that accepts password hashes
        print(f"⚠️  WARNING: User {username} needs to reset password after migration")

        # Временный пароль (пользователь должен будет сменить)
        temp_password = "ChangeMe123!"

        new_user_id = client.create_user(username, temp_password, role)

        if new_user_id:
            print(f"  ✅ Created user: {username} (id: {new_user_id})")

            # Обновляем флаги
            client.update_user(
                new_user_id,
                is_active=bool(is_active),
                require_2fa=bool(require_2fa),
            )

            migrated += 1
        else:
            print(f"  ❌ Failed to create user: {username}")
            skipped += 1

    print("=" * 60)
    print(f"✅ Migration complete!")
    print(f"   Migrated: {migrated}")
    print(f"   Skipped: {skipped}")
    print(f"   Total: {len(users)}")
    print("=" * 60)

    if migrated > 0:
        print("⚠️  IMPORTANT: All migrated users must reset their passwords!")
        print("   Default temporary password: ChangeMe123!")

    conn.close()
    return True


def main():
    parser = argparse.ArgumentParser(description="Migrate Arvis users to authentication server")
    parser.add_argument(
        "--source",
        default="data/users.db",
        help="Source SQLite database (default: data/users.db)",
    )
    parser.add_argument(
        "--server",
        required=True,
        help="Server URL (e.g., http://192.168.1.100:8443)",
    )
    parser.add_argument(
        "--admin-user",
        default="admin",
        help="Admin username (default: admin)",
    )
    parser.add_argument(
        "--admin-pass",
        required=True,
        help="Admin password",
    )

    args = parser.parse_args()

    success = migrate_users(
        args.source,
        args.server,
        args.admin_user,
        args.admin_pass,
    )

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
