"""
Authentication API Endpoints
API эндпоинты аутентификации
"""

import hashlib
import secrets
import uuid
from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from server.config import get_settings
from server.database.models import AuditLog, LoginAttempt, RoleEnum
from server.database.models import Session as SessionModel
from server.database.models import User
from server.database.storage import DatabaseStorage, get_db

router = APIRouter(prefix="/api/auth", tags=["Authentication"])
settings = get_settings()
security = HTTPBearer()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

import bcrypt as bcrypt_direct


# ==================== Pydantic Models ====================


class LoginRequest(BaseModel):
    """Login request model"""

    username: str = Field(..., min_length=3, max_length=100)
    password: str = Field(..., min_length=1)
    device_name: Optional[str] = None
    totp_code: Optional[str] = None


class RegisterRequest(BaseModel):
    """Register request model"""

    username: str = Field(..., min_length=3, max_length=100)
    password: str = Field(..., min_length=8)
    email: Optional[str] = None
    device_name: Optional[str] = None


class LoginResponse(BaseModel):
    """Login response model"""

    user_id: str
    username: str
    role: str
    access_token: str
    refresh_token: Optional[str] = None
    expires_in: int
    require_2fa: bool = False
    session_id: str


class GuestLoginResponse(BaseModel):
    """Guest login response"""

    user_id: str = "guest"
    username: str = "Guest"
    role: str = "guest"
    access_token: str
    expires_in: int
    session_id: str


class UserInfoResponse(BaseModel):
    """User info response"""

    user_id: str
    username: str
    role: str
    email: Optional[str]
    is_active: bool
    require_2fa: bool
    created_at: datetime
    last_login: Optional[datetime]


class PermissionCheckRequest(BaseModel):
    """Permission check request"""

    permission: str


class PermissionCheckResponse(BaseModel):
    """Permission check response"""

    allowed: bool
    user_role: str
    permission: str


class RefreshTokenRequest(BaseModel):
    """Refresh token request"""

    refresh_token: str


# ==================== Helper Functions ====================


def hash_password(password: str, salt: str) -> str:
    """Hash password with salt using bcrypt directly"""
    # Bcrypt has 72 byte limit
    password_bytes = (password + salt).encode('utf-8')[:72]
    return bcrypt_direct.hashpw(password_bytes, bcrypt_direct.gensalt()).decode('utf-8')


def verify_password(plain_password: str, hashed_password: str, salt: str) -> bool:
    """Verify password using bcrypt directly"""
    try:
        # Bcrypt has 72 byte limit
        password_bytes = (plain_password + salt).encode('utf-8')[:72]
        hash_bytes = hashed_password.encode('utf-8')
        result = bcrypt_direct.checkpw(password_bytes, hash_bytes)
        return result
    except Exception as e:
        # Log the error for debugging
        import logging
        logger = logging.getLogger("arvis_auth_server")
        logger.error(f"Password verification error: {e}")
        return False


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Create JWT access token"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.access_token_expire_minutes)

    to_encode.update({"exp": expire, "iat": datetime.utcnow()})
    encoded_jwt = jwt.encode(to_encode, settings.secret_key, algorithm=settings.algorithm)
    return encoded_jwt


def decode_access_token(token: str) -> dict:
    """Decode JWT access token"""
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
        return payload
    except JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid authentication credentials")


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security), db: Session = Depends(get_db)
) -> User:
    """Get current authenticated user"""
    token = credentials.credentials
    payload = decode_access_token(token)

    user_id: str = payload.get("sub")
    if user_id is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid authentication credentials")

    storage = DatabaseStorage(db)
    user = storage.get_user_by_user_id(user_id)

    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")

    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="User account is inactive")

    if user.is_locked:
        if user.locked_until and user.locked_until > datetime.utcnow():
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account is temporarily locked")
        else:
            # Unlock account if lockout period has passed
            user.is_locked = False
            user.locked_until = None
            storage.update_user(user)

    return user


def check_user_permission(user: User, permission: str) -> bool:
    """Check if user has permission based on role"""
    # Permission matrix (same as client-side RBAC)
    role_permissions = {
        RoleEnum.GUEST: {
            "chat.use",
            "chat.history.view",
            "module.weather",
            "module.news",
        },
        RoleEnum.USER: {
            "chat.use",
            "chat.history.view",
            "module.weather",
            "module.news",
            "module.calendar",
            "module.search",
            "system.apps",
            "system.websites",
            "system.lock",
            "history.export",
            "workflow.execute",
            "settings.view",
        },
        RoleEnum.POWER_USER: {
            # All USER permissions plus:
            "code.execute",
            "script.run",
            "workflow.create",
            "workflow.edit",
            "history.import",
            "history.delete",
            "settings.edit",
            "api.use",
        },
        RoleEnum.ADMIN: {
            # All permissions
            "user.view",
            "user.create",
            "user.edit",
            "user.delete",
            "user.role.manage",
            "audit.view",
            "security.manage",
            "system.shutdown",
            "system.restart",
            "settings.advanced",
            "api.manage",
        },
    }

    # Admin has all permissions
    if user.role == RoleEnum.ADMIN:
        return True

    # Check role-specific permissions
    user_perms = role_permissions.get(user.role, set())

    # POWER_USER inherits USER permissions
    if user.role == RoleEnum.POWER_USER:
        user_perms = user_perms.union(role_permissions.get(RoleEnum.USER, set()))

    # ADMIN inherits all
    if user.role == RoleEnum.ADMIN:
        for perms in role_permissions.values():
            user_perms = user_perms.union(perms)

    return permission in user_perms


def record_audit_log(
    db: Session, user: Optional[User], action: str, result: str, details: Optional[str] = None, request: Request = None
):
    """Record audit log entry"""
    storage = DatabaseStorage(db)

    log = AuditLog(
        user_id=user.id if user else None,
        username=user.username if user else None,
        action=action,
        result=result,
        details=details,
        ip_address=request.client.host if request else None,
        user_agent=request.headers.get("User-Agent") if request else None,
    )

    storage.create_audit_log(log)


# ==================== API Endpoints ====================


@router.post("/login", response_model=LoginResponse)
async def login(login_data: LoginRequest, request: Request, db: Session = Depends(get_db)):
    """User login endpoint"""
    storage = DatabaseStorage(db)

    # Check for recent failed attempts
    recent_attempts = storage.get_recent_login_attempts(login_data.username, minutes=settings.lockout_duration_minutes)

    if len(recent_attempts) >= settings.max_login_attempts:
        record_audit_log(db, None, "login", "blocked", f"Too many failed attempts for {login_data.username}", request)
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Too many failed login attempts. Try again in {settings.lockout_duration_minutes} minutes.",
        )

    # Get user
    user = storage.get_user_by_username(login_data.username)

    if not user or not verify_password(login_data.password, user.password_hash, user.salt):
        # Record failed attempt
        attempt = LoginAttempt(
            user_id=user.id if user else None,
            username=login_data.username,
            ip_address=request.client.host,
            user_agent=request.headers.get("User-Agent"),
            success=False,
            failure_reason="Invalid credentials",
        )
        storage.record_login_attempt(attempt)
        record_audit_log(db, user, "login", "failure", "Invalid credentials", request)

        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid username or password")

    # Check if account is locked
    if user.is_locked and user.locked_until and user.locked_until > datetime.utcnow():
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account is temporarily locked")

    # Check if account is active
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account is inactive")

    # Check 2FA if required
    if user.require_2fa:
        if not login_data.totp_code:
            # Return partial response indicating 2FA is required
            return LoginResponse(
                user_id=user.user_id,
                username=user.username,
                role=user.role.value,
                access_token="",
                expires_in=0,
                require_2fa=True,
                session_id="",
            )

        # Verify TOTP code (implementation depends on your TOTP setup)
        # For now, we'll skip actual verification
        pass

    # Clear previous failed attempts
    storage.clear_login_attempts(login_data.username)

    # Create session
    session_id = str(uuid.uuid4())
    expires_at = datetime.utcnow() + timedelta(minutes=settings.session_timeout_minutes)

    access_token_expires = timedelta(minutes=settings.access_token_expire_minutes)
    access_token = create_access_token(
        data={"sub": user.user_id, "username": user.username, "role": user.role.value},
        expires_delta=access_token_expires,
    )

    session = SessionModel(
        session_id=session_id,
        user_id=user.id,
        access_token=access_token,
        ip_address=request.client.host,
        user_agent=request.headers.get("User-Agent"),
        device_name=login_data.device_name,
        expires_at=expires_at,
    )

    storage.create_session(session)

    # Update user last login
    user.last_login = datetime.utcnow()
    storage.update_user(user)

    # Record successful login
    attempt = LoginAttempt(
        user_id=user.id,
        username=login_data.username,
        ip_address=request.client.host,
        user_agent=request.headers.get("User-Agent"),
        success=True,
    )
    storage.record_login_attempt(attempt)
    record_audit_log(db, user, "login", "success", None, request)

    return LoginResponse(
        user_id=user.user_id,
        username=user.username,
        role=user.role.value,
        access_token=access_token,
        expires_in=settings.access_token_expire_minutes * 60,
        require_2fa=False,
        session_id=session_id,
    )


@router.post("/register", response_model=LoginResponse, status_code=status.HTTP_201_CREATED)
async def register(register_data: RegisterRequest, request: Request, db: Session = Depends(get_db)):
    """User registration endpoint (creates user and returns JWT like login)."""
    storage = DatabaseStorage(db)

    # Username uniqueness
    existing_user = storage.get_user_by_username(register_data.username)
    if existing_user:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Username already exists")

    # Email uniqueness (if provided)
    if register_data.email:
        existing_email = storage.get_user_by_email(register_data.email)
        if existing_email:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email already exists")

    salt = secrets.token_hex(32)
    password_hash = hash_password(register_data.password, salt)

    new_user = User(
        user_id=str(uuid.uuid4()),
        username=register_data.username,
        email=register_data.email,
        password_hash=password_hash,
        salt=salt,
        role=RoleEnum.USER,
        is_active=True,
        require_2fa=False,
    )

    storage.create_user(new_user)

    # Create session + access token
    session_id = str(uuid.uuid4())
    expires_at = datetime.utcnow() + timedelta(minutes=settings.session_timeout_minutes)

    access_token_expires = timedelta(minutes=settings.access_token_expire_minutes)
    access_token = create_access_token(
        data={"sub": new_user.user_id, "username": new_user.username, "role": new_user.role.value},
        expires_delta=access_token_expires,
    )

    session = SessionModel(
        session_id=session_id,
        user_id=new_user.id,
        access_token=access_token,
        ip_address=request.client.host,
        user_agent=request.headers.get("User-Agent"),
        device_name=register_data.device_name,
        expires_at=expires_at,
    )
    storage.create_session(session)

    record_audit_log(db, new_user, "register", "success", f"Created user: {new_user.username}", request)

    return LoginResponse(
        user_id=new_user.user_id,
        username=new_user.username,
        role=new_user.role.value,
        access_token=access_token,
        expires_in=settings.access_token_expire_minutes * 60,
        require_2fa=False,
        session_id=session_id,
    )


@router.post("/guest", response_model=GuestLoginResponse)
async def guest_login(request: Request, db: Session = Depends(get_db)):
    """Guest login endpoint"""
    if not settings.guest_enabled:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Guest mode is disabled")

    session_id = str(uuid.uuid4())
    guest_id = f"guest_{session_id[:8]}"

    access_token_expires = timedelta(minutes=settings.guest_session_duration_minutes)
    access_token = create_access_token(
        data={"sub": guest_id, "username": "Guest", "role": RoleEnum.GUEST.value}, expires_delta=access_token_expires
    )

    record_audit_log(db, None, "guest_login", "success", f"Guest session created: {guest_id}", request)

    return GuestLoginResponse(
        user_id=guest_id,
        username="Guest",
        role=RoleEnum.GUEST.value,
        access_token=access_token,
        expires_in=settings.guest_session_duration_minutes * 60,
        session_id=session_id,
    )


@router.post("/logout")
async def logout(request: Request, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Logout endpoint"""
    storage = DatabaseStorage(db)

    # Revoke all active sessions for user
    sessions = storage.get_user_sessions(current_user.id, active_only=True)
    for session in sessions:
        storage.revoke_session(session)

    record_audit_log(db, current_user, "logout", "success", None, request)

    return {"message": "Logged out successfully"}


@router.get("/me", response_model=UserInfoResponse)
async def get_current_user_info(current_user: User = Depends(get_current_user)):
    """Get current user information"""
    return UserInfoResponse(
        user_id=current_user.user_id,
        username=current_user.username,
        role=current_user.role.value,
        email=current_user.email,
        is_active=current_user.is_active,
        require_2fa=current_user.require_2fa,
        created_at=current_user.created_at,
        last_login=current_user.last_login,
    )


@router.post("/check-permission", response_model=PermissionCheckResponse)
async def check_permission(
    permission_data: PermissionCheckRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Check if current user has a specific permission"""
    allowed = check_user_permission(current_user, permission_data.permission)

    # Log permission check
    record_audit_log(
        db,
        current_user,
        "permission_check",
        "allowed" if allowed else "denied",
        f"Permission: {permission_data.permission}",
    )

    return PermissionCheckResponse(
        allowed=allowed, user_role=current_user.role.value, permission=permission_data.permission
    )


@router.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "timestamp": datetime.utcnow().isoformat()}
