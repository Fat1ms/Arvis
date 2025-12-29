"""
User Management API Endpoints
API управления пользователями
"""

import io
import secrets
import uuid
from datetime import datetime
from typing import List, Optional

import pyotp
import qrcode
from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy.orm import Session

from api.auth import get_current_user, hash_password, record_audit_log
from server.config import get_settings
from server.database.models import RoleEnum, User
from server.database.storage import DatabaseStorage, get_db

settings = get_settings()

router = APIRouter(prefix="/api/users", tags=["User Management"])


# ==================== Pydantic Models ====================


class CreateUserRequest(BaseModel):
    """Create user request"""

    username: str = Field(..., min_length=3, max_length=100)
    password: str = Field(..., min_length=8)
    email: Optional[EmailStr] = None
    role: RoleEnum = RoleEnum.USER


class UpdateUserRequest(BaseModel):
    """Update user request"""

    email: Optional[EmailStr] = None
    role: Optional[RoleEnum] = None
    is_active: Optional[bool] = None


class ChangePasswordRequest(BaseModel):
    """Change password request"""

    current_password: str
    new_password: str = Field(..., min_length=8)


class Enable2FARequest(BaseModel):
    """Enable 2FA request"""

    totp_code: str = Field(..., min_length=6, max_length=6)


class Setup2FAResponse(BaseModel):
    """Setup 2FA response"""

    enabled: bool
    secret: Optional[str] = None
    qr_uri: Optional[str] = None


class UserResponse(BaseModel):
    """User response model"""

    user_id: str
    username: str
    email: Optional[str]
    role: str
    is_active: bool
    require_2fa: bool
    created_at: datetime
    last_login: Optional[datetime]


# ==================== Helper Functions ====================


def require_admin(current_user: User = Depends(get_current_user)) -> User:
    """Require admin role"""
    if current_user.role != RoleEnum.ADMIN:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")
    return current_user


# ==================== API Endpoints ====================


@router.post("/", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def create_user(
    user_data: CreateUserRequest,
    request: Request,
    db: Session = Depends(get_db),
    admin_user: User = Depends(require_admin),
):
    """Create a new user (admin only)"""
    storage = DatabaseStorage(db)

    # Check if username already exists
    existing_user = storage.get_user_by_username(user_data.username)
    if existing_user:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Username already exists")

    # Check if email already exists
    if user_data.email:
        existing_email = storage.get_user_by_email(user_data.email)
        if existing_email:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email already exists")

    # Create user
    salt = secrets.token_hex(32)
    password_hash = hash_password(user_data.password, salt)

    new_user = User(
        user_id=str(uuid.uuid4()),
        username=user_data.username,
        email=user_data.email,
        password_hash=password_hash,
        salt=salt,
        role=user_data.role,
        is_active=True,
    )

    storage.create_user(new_user)

    record_audit_log(db, admin_user, "user_create", "success", f"Created user: {new_user.username}", request)

    return UserResponse(
        user_id=new_user.user_id,
        username=new_user.username,
        email=new_user.email,
        role=new_user.role.value,
        is_active=new_user.is_active,
        require_2fa=new_user.require_2fa,
        created_at=new_user.created_at,
        last_login=new_user.last_login,
    )


@router.get("/", response_model=List[UserResponse])
async def list_users(
    skip: int = 0, limit: int = 100, db: Session = Depends(get_db), admin_user: User = Depends(require_admin)
):
    """List all users (admin only)"""
    storage = DatabaseStorage(db)
    users = storage.list_users(skip=skip, limit=limit)

    return [
        UserResponse(
            user_id=user.user_id,
            username=user.username,
            email=user.email,
            role=user.role.value,
            is_active=user.is_active,
            require_2fa=user.require_2fa,
            created_at=user.created_at,
            last_login=user.last_login,
        )
        for user in users
    ]


@router.get("/{user_id}", response_model=UserResponse)
async def get_user(user_id: str, db: Session = Depends(get_db), admin_user: User = Depends(require_admin)):
    """Get user by ID (admin only)"""
    storage = DatabaseStorage(db)
    user = storage.get_user_by_user_id(user_id)

    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    return UserResponse(
        user_id=user.user_id,
        username=user.username,
        email=user.email,
        role=user.role.value,
        is_active=user.is_active,
        require_2fa=user.require_2fa,
        created_at=user.created_at,
        last_login=user.last_login,
    )


@router.put("/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: str,
    update_data: UpdateUserRequest,
    request: Request,
    db: Session = Depends(get_db),
    admin_user: User = Depends(require_admin),
):
    """Update user (admin only)"""
    storage = DatabaseStorage(db)
    user = storage.get_user_by_user_id(user_id)

    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    # Prevent modifying admin user
    if user.username == "admin" and update_data.role and update_data.role != RoleEnum.ADMIN:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Cannot change admin role")

    # Update fields
    if update_data.email is not None:
        user.email = update_data.email
    if update_data.role is not None:
        user.role = update_data.role
    if update_data.is_active is not None:
        user.is_active = update_data.is_active

    storage.update_user(user)

    record_audit_log(db, admin_user, "user_update", "success", f"Updated user: {user.username}", request)

    return UserResponse(
        user_id=user.user_id,
        username=user.username,
        email=user.email,
        role=user.role.value,
        is_active=user.is_active,
        require_2fa=user.require_2fa,
        created_at=user.created_at,
        last_login=user.last_login,
    )


@router.delete("/{user_id}")
async def delete_user(
    user_id: str, request: Request, db: Session = Depends(get_db), admin_user: User = Depends(require_admin)
):
    """Delete user (admin only)"""
    storage = DatabaseStorage(db)
    user = storage.get_user_by_user_id(user_id)

    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    # Prevent deleting admin user
    if user.username == "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Cannot delete admin user")

    storage.delete_user(user)

    record_audit_log(db, admin_user, "user_delete", "success", f"Deleted user: {user.username}", request)

    return {"message": "User deleted successfully"}


@router.post("/change-password")
async def change_password(
    password_data: ChangePasswordRequest,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Change current user's password"""
    storage = DatabaseStorage(db)

    # Verify current password
    from server.api.auth import verify_password

    if not verify_password(password_data.current_password, current_user.password_hash, current_user.salt):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Current password is incorrect")

    # Update password
    current_user.password_hash = hash_password(password_data.new_password, current_user.salt)
    current_user.last_password_change = datetime.utcnow()

    storage.update_user(current_user)

    record_audit_log(db, current_user, "password_change", "success", None, request)

    return {"message": "Password changed successfully"}


@router.get("/2fa/setup", response_model=Setup2FAResponse)
async def setup_2fa(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Get 2FA setup information"""
    # Если 2FA уже включена
    if current_user.require_2fa and current_user.totp_secret:
        return Setup2FAResponse(enabled=True)

    # Генерируем новый секретный ключ
    if not current_user.totp_secret:
        secret = pyotp.random_base32()
        current_user.totp_secret = secret

        storage = DatabaseStorage(db)
        storage.update_user(current_user)
    else:
        secret = current_user.totp_secret

    # Создаём URI для QR-кода
    totp = pyotp.TOTP(secret)
    qr_uri = totp.provisioning_uri(name=current_user.username, issuer_name=settings.totp_issuer)

    return Setup2FAResponse(enabled=False, secret=secret, qr_uri=qr_uri)


@router.post("/2fa/enable")
async def enable_2fa(
    enable_data: Enable2FARequest,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Enable 2FA for current user"""
    if not current_user.totp_secret:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="2FA not set up. Call /2fa/setup first")

    # Проверяем TOTP код
    totp = pyotp.TOTP(current_user.totp_secret)
    if not totp.verify(enable_data.totp_code, valid_window=1):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid TOTP code")

    # Включаем 2FA
    current_user.require_2fa = True

    storage = DatabaseStorage(db)
    storage.update_user(current_user)

    record_audit_log(db, current_user, "2fa_enable", "success", None, request)

    return {"message": "2FA enabled successfully"}


@router.post("/2fa/disable")
async def disable_2fa(
    request: Request, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    """Disable 2FA for current user"""
    if not current_user.require_2fa:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="2FA is not enabled")

    # Отключаем 2FA
    current_user.require_2fa = False
    current_user.totp_secret = None

    storage = DatabaseStorage(db)
    storage.update_user(current_user)

    record_audit_log(db, current_user, "2fa_disable", "success", None, request)

    return {"message": "2FA disabled successfully"}
