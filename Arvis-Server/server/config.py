"""
Compatibility wrapper for server.config
Re-exports symbols from top-level config module.
"""
from importlib import import_module

_cfg = import_module("config")

Settings = getattr(_cfg, "Settings")
get_settings = getattr(_cfg, "get_settings")
init_directories = getattr(_cfg, "init_directories")

__all__ = ["Settings", "get_settings", "init_directories"]
