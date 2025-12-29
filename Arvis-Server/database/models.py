"""
Database Models for Authentication Server
Модели базы данных для сервера аутентификации
"""

from datetime import datetime
from enum import Enum as PyEnum

from sqlalchemy import Boolean, Column, DateTime, Enum, ForeignKey, Integer, String, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

Base = declarative_base()


class RoleEnum(str, PyEnum):
    """User roles enumeration"""

    GUEST = "guest"
    USER = "user"
    POWER_USER = "power_user"
    ADMIN = "admin"


class User(Base):
    """User model"""

    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String(36), unique=True, index=True, nullable=False)  # UUID
    username = Column(String(100), unique=True, index=True, nullable=False)
    email = Column(String(255), unique=True, index=True, nullable=True)
    password_hash = Column(String(255), nullable=False)
    salt = Column(String(64), nullable=False)
    role = Column(Enum(RoleEnum), default=RoleEnum.USER, nullable=False)

    # Status
    is_active = Column(Boolean, default=True, nullable=False)
    is_locked = Column(Boolean, default=False, nullable=False)
    locked_until = Column(DateTime, nullable=True)

    # 2FA
    require_2fa = Column(Boolean, default=False, nullable=False)
    totp_secret = Column(String(255), nullable=True)  # Encrypted
    backup_codes = Column(Text, nullable=True)  # JSON array of hashed codes
    two_factor_setup_at = Column(DateTime, nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    last_login = Column(DateTime, nullable=True)
    last_password_change = Column(DateTime, nullable=True)

    # Relationships
    sessions = relationship("Session", back_populates="user", cascade="all, delete-orphan")
    login_attempts = relationship("LoginAttempt", back_populates="user", cascade="all, delete-orphan")
    audit_logs = relationship("AuditLog", back_populates="user", cascade="all, delete-orphan")

    billing_orders = relationship("BillingOrder", back_populates="user", cascade="all, delete-orphan")
    entitlements = relationship("Entitlement", back_populates="user", cascade="all, delete-orphan")
    download_tokens = relationship("DownloadToken", back_populates="user", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<User(username='{self.username}', role='{self.role.value}')>"


class Session(Base):
    """User session model"""

    __tablename__ = "sessions"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String(36), unique=True, index=True, nullable=False)  # UUID
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    access_token = Column(String(512), nullable=False)
    refresh_token = Column(String(512), nullable=True)

    # Session info
    ip_address = Column(String(45), nullable=True)  # IPv6 support
    user_agent = Column(String(512), nullable=True)
    device_name = Column(String(255), nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    expires_at = Column(DateTime, nullable=False)
    last_activity = Column(DateTime, default=datetime.utcnow, nullable=False)
    revoked_at = Column(DateTime, nullable=True)

    # Status
    is_active = Column(Boolean, default=True, nullable=False)

    # Relationship
    user = relationship("User", back_populates="sessions")

    def __repr__(self):
        return f"<Session(session_id='{self.session_id}', user_id={self.user_id})>"


class LoginAttempt(Base):
    """Login attempt tracking for security"""

    __tablename__ = "login_attempts"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)  # Null for non-existent users
    username = Column(String(100), index=True, nullable=False)
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(String(512), nullable=True)
    success = Column(Boolean, default=False, nullable=False)
    failure_reason = Column(String(255), nullable=True)
    attempted_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationship
    user = relationship("User", back_populates="login_attempts")

    def __repr__(self):
        return f"<LoginAttempt(username='{self.username}', success={self.success})>"


class AuditLog(Base):
    """Audit log for security events"""

    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    username = Column(String(100), index=True, nullable=True)
    action = Column(String(100), index=True, nullable=False)  # login, logout, permission_check, etc.
    resource = Column(String(255), nullable=True)  # What was accessed/modified
    result = Column(String(50), nullable=False)  # success, failure, denied
    details = Column(Text, nullable=True)  # JSON with additional info
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(String(512), nullable=True)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True, nullable=False)

    # Relationship
    user = relationship("User", back_populates="audit_logs")

    def __repr__(self):
        return f"<AuditLog(action='{self.action}', result='{self.result}')>"


class RefreshToken(Base):
    """Refresh token storage for token rotation"""

    __tablename__ = "refresh_tokens"

    id = Column(Integer, primary_key=True, index=True)
    token_hash = Column(String(255), unique=True, index=True, nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    session_id = Column(String(36), index=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    expires_at = Column(DateTime, nullable=False)
    revoked = Column(Boolean, default=False, nullable=False)
    revoked_at = Column(DateTime, nullable=True)

    def __repr__(self):
        return f"<RefreshToken(user_id={self.user_id}, revoked={self.revoked})>"


class CacheEntry(Base):
    """Generic cache table for external API responses"""

    __tablename__ = "cache_entries"

    id = Column(Integer, primary_key=True, index=True)
    namespace = Column(String(50), index=True, nullable=False)  # e.g. 'weather', 'news'
    key = Column(String(255), index=True, nullable=False)  # cache key (e.g., city name or query hash)
    data = Column(Text, nullable=False)  # JSON payload as text
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    expires_at = Column(DateTime, nullable=False)

    def __repr__(self):
        return f"<CacheEntry(ns='{self.namespace}', key='{self.key}')>"


class BillingProvider(str, PyEnum):
    """Supported payment providers."""

    STRIPE = "stripe"
    LIQPAY = "liqpay"


class BillingMode(str, PyEnum):
    """Payment mode."""

    ONE_TIME = "one_time"
    SUBSCRIPTION = "subscription"


class BillingStatus(str, PyEnum):
    """Order/payment status."""

    PENDING = "pending"
    PAID = "paid"
    FAILED = "failed"
    CANCELED = "canceled"
    REFUNDED = "refunded"


class BillingOrder(Base):
    """Represents a payment attempt/order created for a user."""

    __tablename__ = "billing_orders"

    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(String(36), unique=True, index=True, nullable=False)  # UUID

    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    provider = Column(Enum(BillingProvider), nullable=False)
    mode = Column(Enum(BillingMode), nullable=False)

    product_key = Column(String(100), index=True, nullable=False)
    amount_cents = Column(Integer, nullable=True)
    currency = Column(String(10), nullable=True)

    status = Column(Enum(BillingStatus), default=BillingStatus.PENDING, nullable=False)

    provider_checkout_id = Column(String(255), index=True, nullable=True)
    provider_payment_id = Column(String(255), index=True, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    paid_at = Column(DateTime, nullable=True)

    user = relationship("User", back_populates="billing_orders")

    def __repr__(self):
        return f"<BillingOrder(order_id='{self.order_id}', provider='{self.provider.value}', status='{self.status.value}')>"


class BillingEvent(Base):
    """Raw webhook events for audit/debug (minimal)."""

    __tablename__ = "billing_events"

    id = Column(Integer, primary_key=True, index=True)
    provider = Column(Enum(BillingProvider), nullable=False)
    event_id = Column(String(255), index=True, nullable=True)
    order_id = Column(String(36), index=True, nullable=True)
    payload = Column(Text, nullable=False)
    received_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    def __repr__(self):
        return f"<BillingEvent(provider='{self.provider.value}', event_id='{self.event_id}')>"


class Entitlement(Base):
    """Represents user's access right (e.g., eligible to download exe)."""

    __tablename__ = "entitlements"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    product_key = Column(String(100), index=True, nullable=False)
    active_from = Column(DateTime, default=datetime.utcnow, nullable=False)
    active_until = Column(DateTime, nullable=True)  # null = lifetime

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    user = relationship("User", back_populates="entitlements")

    def __repr__(self):
        return f"<Entitlement(user_id={self.user_id}, product_key='{self.product_key}')>"


class DownloadAsset(Base):
    """A downloadable artifact (e.g., Windows .exe)."""

    __tablename__ = "download_assets"

    id = Column(Integer, primary_key=True, index=True)
    asset_key = Column(String(100), unique=True, index=True, nullable=False)
    platform = Column(String(50), index=True, nullable=False)  # windows, linux, mac
    display_name = Column(String(255), nullable=False)
    version = Column(String(50), nullable=True)

    file_path = Column(String(1024), nullable=False)
    file_name = Column(String(255), nullable=False)

    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    tokens = relationship("DownloadToken", back_populates="asset", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<DownloadAsset(asset_key='{self.asset_key}', version='{self.version}')>"


class DownloadToken(Base):
    """One-time (or limited-use) download token."""

    __tablename__ = "download_tokens"

    id = Column(Integer, primary_key=True, index=True)
    token_hash = Column(String(64), unique=True, index=True, nullable=False)  # sha256 hex

    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    asset_id = Column(Integer, ForeignKey("download_assets.id"), nullable=False)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    expires_at = Column(DateTime, nullable=False)
    used_at = Column(DateTime, nullable=True)

    max_uses = Column(Integer, default=1, nullable=False)
    uses = Column(Integer, default=0, nullable=False)

    ip_address = Column(String(45), nullable=True)
    user_agent = Column(String(512), nullable=True)

    user = relationship("User", back_populates="download_tokens")
    asset = relationship("DownloadAsset", back_populates="tokens")

    def __repr__(self):
        return f"<DownloadToken(user_id={self.user_id}, asset_id={self.asset_id}, uses={self.uses}/{self.max_uses})>"
