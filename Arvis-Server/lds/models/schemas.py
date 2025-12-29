"""Pydantic models for API request/response"""

from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, EmailStr, Field


# ============ Authentication ============

class UserRegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8)
    role: str = Field(..., pattern="^(consumer|provider)$")


class UserRegisterResponse(BaseModel):
    user_id: str
    email: str
    api_key: str
    virtual_credits: int
    message: str


class AuthToken(BaseModel):
    access_token: str
    token_type: str
    user_id: str


# ============ Provider Resources ============

class ProviderResourcesRequest(BaseModel):
    ram_gb: int = Field(..., ge=1, le=1024)
    cpu_cores: int = Field(..., ge=1, le=256)
    gpu_count: int = Field(default=0, ge=0, le=10)


class ProviderResourcesResponse(BaseModel):
    provider_id: str
    status: str
    ram_allocated_gb: int
    cpu_cores_allocated: int
    gpu_allocated: int
    message: str


class ProviderHeartbeatRequest(BaseModel):
    ram_used_mb: int
    cpu_percent: float = Field(..., ge=0, le=100)
    gpu_percent: Optional[float] = None
    tasks_processing: int = 0


class ProviderHeartbeatResponse(BaseModel):
    status: str
    next_task_id: Optional[str] = None
    server_time: datetime
    message: str


# ============ Tasks ============

class TaskSubmitRequest(BaseModel):
    model: str
    prompt: str = Field(..., min_length=1, max_length=10000)
    max_tokens: int = Field(default=256, ge=1, le=4096)
    temperature: float = Field(default=0.7, ge=0, le=2.0)
    priority: str = Field(default="normal", pattern="^(low|normal|high|urgent)$")
    timeout_seconds: int = Field(default=300, ge=10, le=1800)


class TaskSubmitResponse(BaseModel):
    task_id: str
    status: str
    simulated_cost_credits: int
    estimated_wait_seconds: int
    message: str


class TaskStatusResponse(BaseModel):
    task_id: str
    status: str
    model: str
    prompt: str
    result: Optional[str] = None
    error_message: Optional[str] = None
    provider_id: Optional[str] = None
    execution_time_seconds: Optional[float] = None
    created_at: datetime
    completed_at: Optional[datetime] = None


class TaskResultSubmitRequest(BaseModel):
    result: str
    execution_seconds: float = Field(..., ge=0.1)
    tokens_generated: int = Field(default=0, ge=0)


class TaskResultSubmitResponse(BaseModel):
    status: str
    task_id: str
    virtual_credits_earned: int
    message: str


# ============ Account / Credits ============

class AccountBalanceResponse(BaseModel):
    virtual_credits: int
    next_daily_bonus_at: Optional[datetime] = None
    daily_bonus_amount: int
    message: str


class TransactionRecord(BaseModel):
    transaction_id: str
    timestamp: datetime
    transaction_type: str
    amount: int
    balance_after: int
    reference_id: Optional[str] = None


class TransactionHistoryResponse(BaseModel):
    total_count: int
    transactions: List[TransactionRecord]


# ============ Provider Info ============

class ProviderEarningsResponse(BaseModel):
    virtual_credits_earned: int
    total_tasks_completed: int
    reputation_score: float
    average_task_time_seconds: float
    uptime_percent: float
    message: str


# ============ Health Check ============

class HealthCheckResponse(BaseModel):
    status: str
    version: str
    timestamp: datetime
    database: str
    redis: str


# ============ Error Response ============

class ErrorResponse(BaseModel):
    detail: str
    error_code: str
    timestamp: datetime
