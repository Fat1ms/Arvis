"""
Security subsystem for Arvis
Подсистема безопасности: RBAC, аутентификация, аудит
"""

from utils.security.audit import AuditEventType, AuditLogger, AuditSeverity, get_audit_logger
from utils.security.auth import AuthManager, Session, User, get_auth_manager
from utils.security.rbac import Permission, RBACManager, Role, get_rbac_manager, require_permission, require_role
from utils.security.storage import UserStorage, get_storage
from utils.security.totp import TOTPManager, get_totp_manager

__all__ = [
    # RBAC
    "Role",
    "Permission",
    "RBACManager",
    "get_rbac_manager",
    "require_permission",
    "require_role",
    # Authentication
    "User",
    "Session",
    "AuthManager",
    "get_auth_manager",
    # Audit
    "AuditEventType",
    "AuditSeverity",
    "AuditLogger",
    "get_audit_logger",
    # Storage
    "UserStorage",
    "get_storage",
    # 2FA (Phase 2 Day 5)
    "TOTPManager",
    "get_totp_manager",
]
