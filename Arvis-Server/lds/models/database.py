"""SQLAlchemy ORM models for database tables"""

import uuid
from datetime import datetime
from sqlalchemy import Column, String, Integer, Float, DateTime, Enum, ForeignKey, Boolean, JSON, Text, Index
from sqlalchemy.orm import relationship

from ..config.database import Base


class User(Base):
    """User accounts (consumers and providers)"""
    __tablename__ = "users"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    email = Column(String(255), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=False)
    api_key = Column(String(128), unique=True, nullable=False, index=True)
    role = Column(String(20), nullable=False)  # 'consumer' or 'provider'
    
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    credits = relationship("UserCredits", back_populates="user", uselist=False, cascade="all, delete-orphan")
    ledger = relationship("CreditLedger", back_populates="user", cascade="all, delete-orphan")
    provider = relationship("Provider", back_populates="user", uselist=False, cascade="all, delete-orphan")


class UserCredits(Base):
    """Current credit balance for each user"""
    __tablename__ = "user_credits"
    
    user_id = Column(String(36), ForeignKey("users.id"), primary_key=True)
    virtual_credits = Column(Integer, nullable=False, default=1000)
    last_daily_bonus = Column(DateTime, nullable=True)
    
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationship
    user = relationship("User", back_populates="credits")


class CreditLedger(Base):
    """Transaction history for credits"""
    __tablename__ = "credit_ledger"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    amount = Column(Integer, nullable=False)  # Positive or negative
    balance_after = Column(Integer, nullable=False)
    
    transaction_type = Column(String(50), nullable=False)  # 'signup_bonus', 'daily_bonus', 'task_submission', etc.
    reference_id = Column(String(36), nullable=True, index=True)  # Task ID if applicable
    
    timestamp = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)
    
    # Relationship
    user = relationship("User", back_populates="ledger")
    
    __table_args__ = (
        Index('idx_user_timestamp', 'user_id', 'timestamp'),
    )


class Provider(Base):
    """Resource providers"""
    __tablename__ = "providers"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey("users.id"), unique=True, nullable=False)
    
    status = Column(String(20), nullable=False, default="pending_verification")  # 'active', 'inactive', 'banned', etc.
    
    ram_allocated_gb = Column(Integer, nullable=False)
    cpu_cores_allocated = Column(Integer, nullable=False)
    gpu_allocated = Column(Integer, nullable=False, default=0)
    
    reputation_score = Column(Float, nullable=False, default=3.0)
    total_tasks_completed = Column(Integer, nullable=False, default=0)
    total_uptime_hours = Column(Integer, nullable=False, default=0)
    
    registration_date = Column(DateTime, nullable=False, default=datetime.utcnow)
    last_heartbeat = Column(DateTime, nullable=True)
    
    # Relationship
    user = relationship("User", back_populates="provider")
    resources = relationship("ProviderResources", back_populates="provider", cascade="all, delete-orphan")
    
    __table_args__ = (
        Index('idx_provider_status', 'status'),
    )


class ProviderResources(Base):
    """Current resource snapshot for provider"""
    __tablename__ = "provider_resources"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    provider_id = Column(String(36), ForeignKey("providers.id"), nullable=False, index=True)
    
    ram_used_mb = Column(Integer, nullable=False)
    ram_limit_mb = Column(Integer, nullable=False)
    cpu_percent = Column(Float, nullable=False)
    gpu_percent = Column(Float, nullable=True)
    
    timestamp = Column(DateTime, nullable=False, default=datetime.utcnow)
    reported_by_provider = Column(Boolean, nullable=False, default=True)
    
    # Relationship
    provider = relationship("Provider", back_populates="resources")
    
    __table_args__ = (
        Index('idx_provider_resources_timestamp', 'provider_id', 'timestamp'),
    )


class Task(Base):
    """Task queue entries"""
    __tablename__ = "tasks"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    consumer_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    provider_id = Column(String(36), ForeignKey("providers.id"), nullable=True, index=True)
    
    status = Column(String(20), nullable=False, default="pending")  # 'pending', 'assigned', 'running', 'completed', 'failed', 'timeout'
    priority = Column(String(10), nullable=False, default="normal")  # 'low', 'normal', 'high', 'urgent'
    
    llm_model = Column(String(100), nullable=False)
    prompt = Column(Text, nullable=False)
    max_tokens = Column(Integer, nullable=False, default=256)
    temperature = Column(Float, nullable=False, default=0.7)
    
    simulated_cost_credits = Column(Integer, nullable=False)
    actual_credits_charged = Column(Integer, nullable=True)
    
    submission_time = Column(DateTime, nullable=False, default=datetime.utcnow)
    assignment_time = Column(DateTime, nullable=True)
    start_time = Column(DateTime, nullable=True)
    completion_time = Column(DateTime, nullable=True)
    timeout_seconds = Column(Integer, nullable=False, default=300)
    
    result = Column(Text, nullable=True)
    error_message = Column(Text, nullable=True)
    
    __table_args__ = (
        Index('idx_task_status_priority', 'status', 'priority'),
        Index('idx_task_consumer_time', 'consumer_id', 'submission_time'),
    )


class AuditLog(Base):
    """Audit trail for all critical actions"""
    __tablename__ = "audit_log"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    timestamp = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)
    
    actor_type = Column(String(50), nullable=False)  # 'provider', 'consumer', 'admin'
    actor_id = Column(String(36), nullable=False, index=True)
    
    action = Column(String(100), nullable=False)
    resource_id = Column(String(36), nullable=True, index=True)
    
    details = Column(JSON, nullable=True)
    
    __table_args__ = (
        Index('idx_audit_timestamp_actor', 'timestamp', 'actor_id'),
    )
