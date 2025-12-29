#!/usr/bin/env python3
"""
Скрипт для исправления API несовместимостей PyQt5 -> PyQt6
"""
import os
import re
from pathlib import Path

def fix_file(filepath):
    """Исправить файл, заменив PyQt5 API на PyQt6"""
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    original = content
    
    # QLineEdit echo mode
    content = re.sub(r'QLineEdit\.Password\b', 'QLineEdit.EchoMode.Password', content)

    # QMessageBox buttons moved under StandardButton enum in PyQt6
    button_map = {
        r'QMessageBox\.Yes\b': 'QMessageBox.StandardButton.Yes',
        r'QMessageBox\.No\b': 'QMessageBox.StandardButton.No',
        r'QMessageBox\.Ok\b': 'QMessageBox.StandardButton.Ok',
        r'QMessageBox\.Cancel\b': 'QMessageBox.StandardButton.Cancel',
        r'QMessageBox\.Close\b': 'QMessageBox.StandardButton.Close',
        r'QMessageBox\.Retry\b': 'QMessageBox.StandardButton.Retry',
        r'QMessageBox\.Ignore\b': 'QMessageBox.StandardButton.Ignore',
        r'QMessageBox\.Abort\b': 'QMessageBox.StandardButton.Abort',
        r'QMessageBox\.Save\b': 'QMessageBox.StandardButton.Save',
        r'QMessageBox\.Open\b': 'QMessageBox.StandardButton.Open',
        r'QMessageBox\.Apply\b': 'QMessageBox.StandardButton.Apply',
        r'QMessageBox\.Reset\b': 'QMessageBox.StandardButton.Reset',
        r'QMessageBox\.RestoreDefaults\b': 'QMessageBox.StandardButton.RestoreDefaults',
        r'QMessageBox\.Help\b': 'QMessageBox.StandardButton.Help',
        r'QMessageBox\.NoButton\b': 'QMessageBox.StandardButton.NoButton',
    }
    for pattern, repl in button_map.items():
        content = re.sub(pattern, repl, content)

    # QDialog result codes moved under DialogCode enum in PyQt6
    content = re.sub(r'QDialog\.Accepted\b', 'QDialog.DialogCode.Accepted', content)
    content = re.sub(r'QDialog\.Rejected\b', 'QDialog.DialogCode.Rejected', content)

    # Qt.WindowType.Window flags moved under WindowType in PyQt6
    window_flag_map = {
        r'Qt\.FramelessWindowHint\b': 'Qt.WindowType.FramelessWindowHint',
        r'Qt\.CustomizeWindowHint\b': 'Qt.WindowType.CustomizeWindowHint',
        r'Qt\.WindowStaysOnTopHint\b': 'Qt.WindowType.WindowStaysOnTopHint',
        r'Qt\.WindowMinimizeButtonHint\b': 'Qt.WindowType.WindowMinimizeButtonHint',
        r'Qt\.WindowMaximizeButtonHint\b': 'Qt.WindowType.WindowMaximizeButtonHint',
        r'Qt\.WindowCloseButtonHint\b': 'Qt.WindowType.WindowCloseButtonHint',
        r'Qt\.WindowTitleHint\b': 'Qt.WindowType.WindowTitleHint',
        r'Qt\.Dialog\b': 'Qt.WindowType.Dialog',
        r'Qt\.Tool\b': 'Qt.WindowType.Tool',
        r'Qt\.Window\b': 'Qt.WindowType.Window',
        r'Qt\.SplashScreen\b': 'Qt.WindowType.SplashScreen',
        r'Qt\.SubWindow\b': 'Qt.WindowType.SubWindow',
    }
    for pattern, repl in window_flag_map.items():
        content = re.sub(pattern, repl, content)
    
    if content != original:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"✓ Исправлен: {filepath}")
        return True
    return False

def main():
    """Основная функция"""
    count = 0
    for root, dirs, files in os.walk('.'):
        # Пропускаем папки pycache и .git
        dirs[:] = [d for d in dirs if d not in ['__pycache__', '.git', '.venv', 'venv']]
        
        for file in files:
            if file.endswith('.py'):
                filepath = os.path.join(root, file)
                if fix_file(filepath):
                    count += 1
    
    print(f"\nВсего исправлено файлов: {count}")

if __name__ == '__main__':
    main()
