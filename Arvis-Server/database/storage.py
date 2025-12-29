"""
Database Storage Layer
Слой работы с базой данных
"""

import hashlib
import secrets
from datetime import datetime, timedelta
from typing import List, Optional

from sqlalchemy import create_engine, func
from sqlalchemy.orm import Session, sessionmaker

from server.config import get_settings
from server.database.models import (
    AuditLog,
    Base,
    BillingEvent,
    BillingMode,
    BillingOrder,
    BillingProvider,
    BillingStatus,
    CacheEntry,
    DownloadAsset,
    DownloadToken,
    Entitlement,
    LoginAttempt,
    RefreshToken,
)
from server.database.models import Session as SessionModel
from server.database.models import User

settings = get_settings()

# Create engine
engine = create_engine(
    settings.database_url,
    connect_args={"check_same_thread": False} if "sqlite" in settings.database_url else {},
    echo=settings.log_level == "DEBUG",
)

# Session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def init_database():
    """Initialize database schema"""
    Base.metadata.create_all(bind=engine)


def get_db():
    """Database dependency for FastAPI"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


class DatabaseStorage:
    """Database storage operations"""

    def __init__(self, db: Session):
        self.db = db

    # ==================== User Operations ====================

    def get_user_by_username(self, username: str) -> Optional[User]:
        """Get user by username"""
        return self.db.query(User).filter(User.username == username).first()

    def get_user_by_id(self, user_id: int) -> Optional[User]:
        """Get user by ID"""
        return self.db.query(User).filter(User.id == user_id).first()

    def get_user_by_user_id(self, user_id: str) -> Optional[User]:
        """Get user by UUID"""
        return self.db.query(User).filter(User.user_id == user_id).first()

    def get_user_by_email(self, email: str) -> Optional[User]:
        """Get user by email"""
        return self.db.query(User).filter(User.email == email).first()

    def create_user(self, user: User) -> User:
        """Create new user"""
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)
        return user

    def update_user(self, user: User) -> User:
        """Update user"""
        self.db.commit()
        self.db.refresh(user)
        return user

    def delete_user(self, user: User):
        """Delete user"""
        self.db.delete(user)
        self.db.commit()

    def list_users(self, skip: int = 0, limit: int = 100) -> List[User]:
        """List all users"""
        return self.db.query(User).offset(skip).limit(limit).all()

    def count_users(self) -> int:
        """Count total users"""
        return self.db.query(User).count()

    # ==================== Session Operations ====================

    def create_session(self, session: SessionModel) -> SessionModel:
        """Create new session"""
        self.db.add(session)
        self.db.commit()
        self.db.refresh(session)
        return session

    def get_session(self, session_id: str) -> Optional[SessionModel]:
        """Get session by ID"""
        return self.db.query(SessionModel).filter(SessionModel.session_id == session_id).first()

    def get_user_sessions(self, user_id: int, active_only: bool = True) -> List[SessionModel]:
        """Get all sessions for a user"""
        query = self.db.query(SessionModel).filter(SessionModel.user_id == user_id)
        if active_only:
            query = query.filter(SessionModel.is_active == True, SessionModel.expires_at > datetime.utcnow())
        return query.all()

    def update_session_activity(self, session: SessionModel):
        """Update session last activity"""
        session.last_activity = datetime.utcnow()
        self.db.commit()

    def revoke_session(self, session: SessionModel):
        """Revoke a session"""
        session.is_active = False
        session.revoked_at = datetime.utcnow()
        self.db.commit()

    def cleanup_expired_sessions(self):
        """Clean up expired sessions"""
        self.db.query(SessionModel).filter(SessionModel.expires_at < datetime.utcnow()).update(
            {"is_active": False, "revoked_at": datetime.utcnow()}
        )
        self.db.commit()

    # ==================== Login Attempt Operations ====================

    def record_login_attempt(self, attempt: LoginAttempt) -> LoginAttempt:
        """Record a login attempt"""
        self.db.add(attempt)
        self.db.commit()
        self.db.refresh(attempt)
        return attempt

    def get_recent_login_attempts(self, username: str, minutes: int = 15) -> List[LoginAttempt]:
        """Get recent failed login attempts"""
        cutoff = datetime.utcnow() - timedelta(minutes=minutes)
        return (
            self.db.query(LoginAttempt)
            .filter(
                LoginAttempt.username == username, LoginAttempt.success == False, LoginAttempt.attempted_at > cutoff
            )
            .all()
        )

    def clear_login_attempts(self, username: str):
        """Clear login attempts for user"""
        self.db.query(LoginAttempt).filter(LoginAttempt.username == username).delete()
        self.db.commit()

    # ==================== Audit Log Operations ====================

    def create_audit_log(self, log: AuditLog) -> AuditLog:
        """Create audit log entry"""
        self.db.add(log)
        self.db.commit()
        self.db.refresh(log)
        return log

    def get_audit_logs(
        self, user_id: Optional[int] = None, action: Optional[str] = None, skip: int = 0, limit: int = 100
    ) -> List[AuditLog]:
        """Get audit logs with filters"""
        query = self.db.query(AuditLog)

        if user_id is not None:
            query = query.filter(AuditLog.user_id == user_id)
        if action is not None:
            query = query.filter(AuditLog.action == action)

        return query.order_by(AuditLog.timestamp.desc()).offset(skip).limit(limit).all()

    def cleanup_old_audit_logs(self, days: int = 90):
        """Clean up old audit logs"""
        cutoff = datetime.utcnow() - timedelta(days=days)
        self.db.query(AuditLog).filter(AuditLog.timestamp < cutoff).delete()
        self.db.commit()

    # ==================== Refresh Token Operations ====================

    def create_refresh_token(self, token: RefreshToken) -> RefreshToken:
        """Create refresh token"""
        self.db.add(token)
        self.db.commit()
        self.db.refresh(token)
        return token

    def get_refresh_token(self, token_hash: str) -> Optional[RefreshToken]:
        """Get refresh token by hash"""
        return self.db.query(RefreshToken).filter(RefreshToken.token_hash == token_hash).first()

    def revoke_refresh_token(self, token: RefreshToken):
        """Revoke a refresh token"""
        token.revoked = True
        token.revoked_at = datetime.utcnow()
        self.db.commit()

    def cleanup_expired_refresh_tokens(self):
        """Clean up expired refresh tokens"""
        self.db.query(RefreshToken).filter(RefreshToken.expires_at < datetime.utcnow()).delete()
        self.db.commit()

    # ==================== Cache Operations ====================

    def get_cache(self, namespace: str, key: str) -> Optional[CacheEntry]:
        """Get non-expired cache entry by namespace and key"""
        return (
            self.db.query(CacheEntry)
            .filter(
                CacheEntry.namespace == namespace,
                CacheEntry.key == key,
                CacheEntry.expires_at > datetime.utcnow(),
            )
            .first()
        )

    def set_cache(self, namespace: str, key: str, data: str, ttl_seconds: int) -> CacheEntry:
        """Create or update cache entry"""
        expires_at = datetime.utcnow() + timedelta(seconds=ttl_seconds)
        entry = (
            self.db.query(CacheEntry)
            .filter(
                CacheEntry.namespace == namespace,
                CacheEntry.key == key,
            )
            .first()
        )

        if entry:
            entry.data = data
            entry.expires_at = expires_at
        else:
            entry = CacheEntry(namespace=namespace, key=key, data=data, expires_at=expires_at)
            self.db.add(entry)

        self.db.commit()
        self.db.refresh(entry)
        return entry

    def cleanup_expired_cache(self):
        """Remove expired cache entries"""
        self.db.query(CacheEntry).filter(CacheEntry.expires_at <= datetime.utcnow()).delete()
        self.db.commit()

    # ==================== Billing / Entitlements ====================

    def create_billing_order(self, order: BillingOrder) -> BillingOrder:
        self.db.add(order)
        self.db.commit()
        self.db.refresh(order)
        return order

    def get_billing_order_by_order_id(self, order_id: str) -> Optional[BillingOrder]:
        return self.db.query(BillingOrder).filter(BillingOrder.order_id == order_id).first()

    def get_billing_order_by_provider_checkout_id(self, provider: BillingProvider, checkout_id: str) -> Optional[BillingOrder]:
        return (
            self.db.query(BillingOrder)
            .filter(BillingOrder.provider == provider, BillingOrder.provider_checkout_id == checkout_id)
            .first()
        )

    def mark_billing_order_paid(self, order: BillingOrder, provider_payment_id: Optional[str] = None) -> BillingOrder:
        order.status = BillingStatus.PAID
        order.paid_at = datetime.utcnow()
        if provider_payment_id:
            order.provider_payment_id = provider_payment_id
        self.db.commit()
        self.db.refresh(order)
        return order

    def record_billing_event(self, event: BillingEvent) -> BillingEvent:
        self.db.add(event)
        self.db.commit()
        self.db.refresh(event)
        return event

    def upsert_entitlement(
        self,
        user_id: int,
        product_key: str,
        active_until: Optional[datetime] = None,
    ) -> Entitlement:
        now = datetime.utcnow()
        ent = (
            self.db.query(Entitlement)
            .filter(Entitlement.user_id == user_id, Entitlement.product_key == product_key)
            .first()
        )
        if ent:
            ent.active_from = ent.active_from or now
            # If any purchase grants lifetime, keep lifetime.
            if ent.active_until is None:
                pass
            else:
                if active_until is None:
                    ent.active_until = None
                else:
                    ent.active_until = max(ent.active_until, active_until)
        else:
            ent = Entitlement(user_id=user_id, product_key=product_key, active_from=now, active_until=active_until)
            self.db.add(ent)

        self.db.commit()
        self.db.refresh(ent)
        return ent

    def has_active_entitlement(self, user_id: int, product_key: str, at_time: Optional[datetime] = None) -> bool:
        now = at_time or datetime.utcnow()
        ent = (
            self.db.query(Entitlement)
            .filter(Entitlement.user_id == user_id, Entitlement.product_key == product_key)
            .first()
        )
        if not ent:
            return False
        if ent.active_until is None:
            return True
        return ent.active_until > now

    # ==================== Download assets / tokens ====================

    def get_download_asset_by_key(self, asset_key: str) -> Optional[DownloadAsset]:
        return self.db.query(DownloadAsset).filter(DownloadAsset.asset_key == asset_key).first()

    def get_active_download_asset_by_key(self, asset_key: str) -> Optional[DownloadAsset]:
        return (
            self.db.query(DownloadAsset)
            .filter(DownloadAsset.asset_key == asset_key, DownloadAsset.is_active == True)
            .first()
        )

    def create_or_update_download_asset(self, asset: DownloadAsset) -> DownloadAsset:
        existing = self.get_download_asset_by_key(asset.asset_key)
        if existing:
            existing.platform = asset.platform
            existing.display_name = asset.display_name
            existing.version = asset.version
            existing.file_path = asset.file_path
            existing.file_name = asset.file_name
            existing.is_active = asset.is_active
            self.db.commit()
            self.db.refresh(existing)
            return existing

        self.db.add(asset)
        self.db.commit()
        self.db.refresh(asset)
        return asset

    def create_download_token(
        self,
        user_id: int,
        asset_id: object,
        ttl_seconds: int,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        max_uses: int = 1,
    ) -> tuple[DownloadToken, str]:
        raw = secrets.token_urlsafe(32)
        token_hash = hashlib.sha256(raw.encode("utf-8")).hexdigest()
        expires_at = datetime.utcnow() + timedelta(seconds=ttl_seconds)

        token = DownloadToken(
            token_hash=token_hash,
            user_id=user_id,
            asset_id=int(asset_id),
            expires_at=expires_at,
            max_uses=max_uses,
            uses=0,
            ip_address=ip_address,
            user_agent=user_agent,
        )
        self.db.add(token)
        self.db.commit()
        self.db.refresh(token)
        return token, raw

    def get_download_token_by_raw(self, raw_token: str) -> Optional[DownloadToken]:
        token_hash = hashlib.sha256(raw_token.encode("utf-8")).hexdigest()
        return self.db.query(DownloadToken).filter(DownloadToken.token_hash == token_hash).first()

    def validate_download_token(self, raw_token: str) -> Optional[DownloadToken]:
        token = self.get_download_token_by_raw(raw_token)
        if not token:
            return None
        now = datetime.utcnow()
        if token.expires_at <= now:
            return None
        if token.uses >= token.max_uses:
            return None
        return token

    def consume_download_token(self, token: DownloadToken) -> DownloadToken:
        token.uses += 1
        if token.uses >= token.max_uses:
            token.used_at = datetime.utcnow()
        self.db.commit()
        self.db.refresh(token)
        return token
