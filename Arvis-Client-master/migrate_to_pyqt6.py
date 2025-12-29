#!/usr/bin/env python3
"""
Скрипт миграции Arvis с PyQt5 на PyQt6
Автоматически обновляет импорты и некоторые API вызовы
"""

import os
import re
from pathlib import Path
from typing import List, Tuple

# Паттерны для замены
REPLACEMENTS = [
    # Основные импорты
    (r'from PyQt5\.QtCore', 'from PyQt6.QtCore'),
    (r'from PyQt5\.QtGui', 'from PyQt6.QtGui'),
    (r'from PyQt5\.QtWidgets', 'from PyQt6.QtWidgets'),
    (r'from PyQt5\.QtSvg', 'from PyQt6.QtSvgWidgets'),  # ВАЖНО: QtSvg → QtSvgWidgets
    (r'import PyQt6', 'import PyQt6'),
    
    # API изменения
    (r'\.exec_\(\)', '.exec()'),  # exec_() → exec()
    (r'QApplication\.exec_\(\)', 'QApplication.exec()'),
    (r'QDialog\.exec_\(\)', 'QDialog.exec()'),
    
    # Enum изменения (PyQt6 использует namespace enums)
    (r'Qt\.AlignCenter', 'Qt.AlignmentFlag.AlignCenter'),
    (r'Qt\.AlignLeft', 'Qt.AlignmentFlag.AlignLeft'),
    (r'Qt\.AlignRight', 'Qt.AlignmentFlag.AlignRight'),
    (r'Qt\.AlignTop', 'Qt.AlignmentFlag.AlignTop'),
    (r'Qt\.AlignBottom', 'Qt.AlignmentFlag.AlignBottom'),
    (r'Qt\.AlignVCenter', 'Qt.AlignmentFlag.AlignVCenter'),
    (r'Qt\.AlignHCenter', 'Qt.AlignmentFlag.AlignHCenter'),
]

# Файлы для исключения из обработки
EXCLUDE_PATTERNS = [
    '*.pyc',
    '__pycache__',
    '.git',
    '.venv',
    'venv',
    'node_modules',
    '*.md',  # Markdown файлы не трогаем (там только примеры)
    '*.bat',  # Batch файлы обновим вручную
]

def should_process_file(file_path: Path) -> bool:
    """Проверяет, нужно ли обрабатывать файл"""
    # Только Python файлы
    if file_path.suffix != '.py':
        return False
    
    # Проверяем исключения
    for pattern in EXCLUDE_PATTERNS:
        if pattern in str(file_path):
            return False
    
    return True

def migrate_file(file_path: Path, dry_run: bool = False) -> Tuple[bool, List[str]]:
    """
    Мигрирует один файл с PyQt5 на PyQt6
    
    Returns:
        (changed, changes_list): Был ли файл изменён и список изменений
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
    except Exception as e:
        return False, [f"ERROR reading: {e}"]
    
    original_content = content
    changes = []
    
    # Применяем все замены
    for pattern, replacement in REPLACEMENTS:
        matches = list(re.finditer(pattern, content))
        if matches:
            content = re.sub(pattern, replacement, content)
            changes.append(f"  {pattern} → {replacement} ({len(matches)} occurrences)")
    
    # Если были изменения
    if content != original_content:
        if not dry_run:
            try:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(content)
            except Exception as e:
                return False, [f"ERROR writing: {e}"]
        
        return True, changes
    
    return False, []

def migrate_project(project_root: Path, dry_run: bool = False):
    """Мигрирует весь проект"""
    print(f"🔍 Scanning project: {project_root}")
    print(f"   Mode: {'DRY RUN' if dry_run else 'LIVE MIGRATION'}")
    print()
    
    # Собираем все Python файлы
    python_files = []
    for root, dirs, files in os.walk(project_root):
        # Исключаем директории
        dirs[:] = [d for d in dirs if d not in EXCLUDE_PATTERNS]
        
        for file in files:
            file_path = Path(root) / file
            if should_process_file(file_path):
                python_files.append(file_path)
    
    print(f"📁 Found {len(python_files)} Python files to process")
    print()
    
    # Обрабатываем файлы
    changed_files = []
    for file_path in python_files:
        relative_path = file_path.relative_to(project_root)
        changed, changes = migrate_file(file_path, dry_run)
        
        if changed:
            changed_files.append(file_path)
            print(f"✏️  {relative_path}")
            for change in changes:
                print(change)
            print()
    
    # Итоги
    print()
    print("=" * 60)
    print(f"✅ Migration {'preview' if dry_run else 'completed'}!")
    print(f"   Files changed: {len(changed_files)}/{len(python_files)}")
    print("=" * 60)
    
    if dry_run:
        print()
        print("ℹ️  This was a DRY RUN. No files were actually modified.")
        print("   Run without --dry-run to apply changes.")

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='Migrate Arvis from PyQt5 to PyQt6')
    parser.add_argument('--dry-run', action='store_true', help='Preview changes without modifying files')
    parser.add_argument('--project-root', type=Path, default=Path(__file__).parent, 
                        help='Project root directory (default: script directory)')
    
    args = parser.parse_args()
    
    print("🚀 Arvis PyQt5 → PyQt6 Migration Tool")
    print("=" * 60)
    print()
    
    migrate_project(args.project_root, dry_run=args.dry_run)

if __name__ == '__main__':
    main()
