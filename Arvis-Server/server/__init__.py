"""
Compatibility package wrapper for Arvis Server.
This exposes the 'server.*' import path by re-exporting modules
from the existing project structure.

Goal: allow imports like 'from server.api import auth' to work
without moving files immediately.
"""

__all__ = [
    "api",
    "config",
    "database",
    "core",
    "version",
]
