"""
Windows autostart management for Arvis Launcher
"""

from __future__ import annotations

import sys
import os
from pathlib import Path
from typing import Optional

# Registry path for Windows autostart
REGISTRY_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
APP_NAME = "ArvisLauncher"


def get_launcher_executable() -> Optional[Path]:
    """
    Get the path to the launcher executable.
    Returns None if not running as frozen exe.
    """
    if getattr(sys, 'frozen', False):
        # Running as PyInstaller executable
        return Path(sys.executable)
    else:
        # Running as script - return the main.py path
        # This won't work for autostart, but useful for testing
        return Path(__file__).parent.parent.parent / "main.py"


def is_autostart_enabled() -> bool:
    """Check if autostart is enabled in Windows registry"""
    if os.name != 'nt':
        return False
    
    try:
        import winreg
        
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            REGISTRY_KEY,
            0,
            winreg.KEY_READ
        )
        try:
            value, _ = winreg.QueryValueEx(key, APP_NAME)
            winreg.CloseKey(key)
            return bool(value)
        except FileNotFoundError:
            winreg.CloseKey(key)
            return False
    except Exception:
        return False


def enable_autostart() -> bool:
    """
    Enable autostart by adding registry entry.
    Returns True if successful.
    """
    if os.name != 'nt':
        return False
    
    exe_path = get_launcher_executable()
    if not exe_path or not exe_path.exists():
        return False
    
    # Only allow autostart for frozen executables
    if not getattr(sys, 'frozen', False):
        return False
    
    try:
        import winreg
        
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            REGISTRY_KEY,
            0,
            winreg.KEY_SET_VALUE
        )
        
        # Add the launcher path with --minimized flag
        command = f'"{exe_path}" --minimized'
        winreg.SetValueEx(key, APP_NAME, 0, winreg.REG_SZ, command)
        winreg.CloseKey(key)
        return True
    except Exception as e:
        print(f"Failed to enable autostart: {e}")
        return False


def disable_autostart() -> bool:
    """
    Disable autostart by removing registry entry.
    Returns True if successful (or if entry doesn't exist).
    """
    if os.name != 'nt':
        return False
    
    try:
        import winreg
        
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            REGISTRY_KEY,
            0,
            winreg.KEY_SET_VALUE
        )
        
        try:
            winreg.DeleteValue(key, APP_NAME)
        except FileNotFoundError:
            pass  # Value doesn't exist, that's fine
        
        winreg.CloseKey(key)
        return True
    except Exception as e:
        print(f"Failed to disable autostart: {e}")
        return False


def set_autostart(enabled: bool) -> bool:
    """
    Set autostart state.
    Returns True if successful.
    """
    if enabled:
        return enable_autostart()
    else:
        return disable_autostart()


def sync_autostart_with_config(run_on_system_start: bool) -> bool:
    """
    Synchronize autostart registry with config setting.
    Returns True if registry matches config after sync.
    """
    current_state = is_autostart_enabled()
    
    if current_state == run_on_system_start:
        return True  # Already in sync
    
    return set_autostart(run_on_system_start)
