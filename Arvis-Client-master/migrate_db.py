"""
Скрипт миграции БД - добавление колонок для 2FA
"""

import sqlite3
from pathlib import Path


def migrate_database():
    """Добавить недостающие колонки для 2FA"""
    db_path = Path("data") / "users.db"

    if not db_path.exists():
        print("❌ База данных не найдена!")
        return False

    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Проверяем текущие колонки
        cursor.execute("PRAGMA table_info(users)")
        columns = [col[1] for col in cursor.fetchall()]
        print(f"Текущие колонки: {columns}")

        # Добавляем недостающие колонки
        changes_made = False

        if "backup_codes" not in columns:
            print("Добавляю колонку backup_codes...")
            cursor.execute("ALTER TABLE users ADD COLUMN backup_codes TEXT")
            changes_made = True
            print("✅ Колонка backup_codes добавлена")
        else:
            print("✓ Колонка backup_codes уже существует")

        if "two_factor_setup_at" not in columns:
            print("Добавляю колонку two_factor_setup_at...")
            cursor.execute("ALTER TABLE users ADD COLUMN two_factor_setup_at TEXT")
            changes_made = True
            print("✅ Колонка two_factor_setup_at добавлена")
        else:
            print("✓ Колонка two_factor_setup_at уже существует")

        if changes_made:
            conn.commit()
            print()
            print("✅ Миграция завершена успешно!")
        else:
            print()
            print("ℹ️  Миграция не требуется - все колонки на месте")

        # Проверяем результат
        cursor.execute("PRAGMA table_info(users)")
        columns = [col[1] for col in cursor.fetchall()]
        print(f"Финальные колонки: {columns}")

        conn.close()
        return True

    except Exception as e:
        print(f"❌ Ошибка миграции: {e}")
        import traceback

        traceback.print_exc()
        return False


if __name__ == "__main__":
    print("=== Миграция БД для поддержки 2FA ===")
    print()
    migrate_database()
