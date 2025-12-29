#!/usr/bin/env python
"""
Auto-activate venv wrapper for Arvis
Перезапускает приложение в venv если это необходимо
"""
import sys
import os
import subprocess
from pathlib import Path


def _get_existing_venv_dir(base_dir: Path) -> Path | None:
    """Return .venv or venv directory if it exists (prefer .venv)."""
    for name in (".venv", "venv"):
        candidate = base_dir / name
        if candidate.exists():
            return candidate
    return None

def should_use_venv():
    """Проверить нужно ли использовать venv"""
    # Если мы уже в venv, то ничего не делаем
    if hasattr(sys, 'real_prefix') or (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix):
        return False
    
    # Проверить есть ли venv в текущей директории (.venv предпочтительнее)
    base_dir = Path(__file__).parent
    return _get_existing_venv_dir(base_dir) is not None

def get_venv_python():
    """Получить путь к python в venv"""
    base_dir = Path(__file__).parent
    venv_path = _get_existing_venv_dir(base_dir)
    if not venv_path:
        return None
    if sys.platform == "win32":
        python_exe = venv_path / "Scripts" / "python.exe"
    else:
        python_exe = venv_path / "bin" / "python"
    return str(python_exe) if python_exe.exists() else None

def restart_in_venv():
    """Перезапустить приложение в venv"""
    venv_python = get_venv_python()
    if not venv_python:
        print("ERROR: venv python not found!")
        return False
    
    print(f"[INFO] Switching to venv Python: {venv_python}")
    
    # Перезапустить с venv python
    cmd = [venv_python] + sys.argv
    try:
        result = subprocess.run(cmd)
        sys.exit(result.returncode)
    except Exception as e:
        print(f"ERROR: Failed to restart in venv: {e}")
        return False

if __name__ == "__main__":
    # Если нужно использовать venv и мы не в нём, перезапустимся
    if should_use_venv():
        restart_in_venv()
    
    # Иначе импортируем и запускаем main.py
    # Добавляем текущую директорию в path для импорта
    sys.path.insert(0, str(Path(__file__).parent))
    
    # Импортируем и запускаем main
    from main import main
    main()
