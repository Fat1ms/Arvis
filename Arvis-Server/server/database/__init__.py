"""
Compatibility layer for server.database
Re-exports from top-level database package.
"""
from importlib import import_module

_models = import_module("database.models")
_storage = import_module("database.storage")

# Re-export commonly used names
AuditLog = getattr(_models, "AuditLog")
Base = getattr(_models, "Base")
LoginAttempt = getattr(_models, "LoginAttempt")
RoleEnum = getattr(_models, "RoleEnum")
Session = getattr(_models, "Session")
User = getattr(_models, "User")

DatabaseStorage = getattr(_storage, "DatabaseStorage")
get_db = getattr(_storage, "get_db")
init_database = getattr(_storage, "init_database")
SessionLocal = getattr(_storage, "SessionLocal")

__all__ = [
    "AuditLog",
    "Base",
    "LoginAttempt",
    "RoleEnum",
    "Session",
    "User",
    "DatabaseStorage",
    "get_db",
    "init_database",
    "SessionLocal",
]
