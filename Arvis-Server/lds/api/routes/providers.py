"""Provider API endpoints"""

from fastapi import APIRouter, Depends, HTTPException, Header
from sqlalchemy.orm import Session

from lds.config.database import get_db
from lds.models.schemas import (
    ProviderResourcesRequest,
    ProviderResourcesResponse,
    ProviderHeartbeatRequest,
    ProviderHeartbeatResponse,
    ProviderEarningsResponse,
    TaskResultSubmitRequest,
)
from lds.models.database import Provider, ProviderResources, Task, User, UserCredits, CreditLedger
from lds.services.security import verify_token
from datetime import datetime, timedelta

router = APIRouter(prefix="/providers", tags=["providers"])


def get_current_provider(
    authorization: str = Header(None),
    db: Session = Depends(get_db),
):
    """Get current provider from API key"""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing API key")
    
    api_key = authorization.replace("Bearer ", "")
    
    user = db.query(User).filter(User.api_key == api_key).first()
    if not user:
        raise HTTPException(status_code=401, detail="Invalid API key")
    
    provider = db.query(Provider).filter(Provider.user_id == user.id).first()
    if not provider:
        raise HTTPException(status_code=404, detail="Provider not registered")
    
    return provider


@router.post("/register-resources", response_model=ProviderResourcesResponse)
def register_provider_resources(
    request: ProviderResourcesRequest,
    db: Session = Depends(get_db),
    provider: Provider = Depends(get_current_provider),
):
    """Register provider resources (RAM, CPU available for tasks)"""
    
    # Update provider allocation
    provider.ram_allocated_gb = request.ram_gb
    provider.cpu_cores_allocated = request.cpu_cores
    provider.gpu_allocated = request.gpu_count if hasattr(request, 'gpu_count') else 0
    provider.status = "active"
    provider.last_heartbeat = datetime.utcnow()
    
    db.commit()
    
    return ProviderResourcesResponse(
        provider_id=str(provider.id),
        ram_allocated_gb=provider.ram_allocated_gb,
        cpu_cores_allocated=provider.cpu_cores_allocated,
        gpu_allocated=provider.gpu_allocated,
        status=provider.status,
        message="Provider resources registered successfully",
    )


@router.post("/heartbeat", response_model=ProviderHeartbeatResponse)
def provider_heartbeat(
    request: ProviderHeartbeatRequest,
    db: Session = Depends(get_db),
    provider: Provider = Depends(get_current_provider),
):
    """Provider sends heartbeat with current resource metrics"""
    
    # Update provider last seen
    provider.last_heartbeat = datetime.utcnow()
    # Provider is active if sending heartbeat
    provider.status = "active"
    
    # Record resource metrics
    metrics = ProviderResources(
        provider_id=provider.id,
        ram_used_mb=request.ram_used_mb,
        ram_limit_mb=provider.ram_allocated_gb * 1024,  # Convert GB to MB
        cpu_percent=request.cpu_percent,
        gpu_percent=request.gpu_percent or 0.0,
        reported_by_provider=True,
    )
    db.add(metrics)
    
    db.commit()
    
    # Find next available task for this provider
    next_task = db.query(Task).filter(
        Task.status == "pending",
        Task.provider_id == None,
    ).first()
    
    return ProviderHeartbeatResponse(
        status="acknowledged",
        next_task_id=str(next_task.id) if next_task else None,
        server_time=datetime.utcnow(),
        message="Heartbeat received successfully",
    )


@router.get("/tasks/next", response_model=dict)
def get_next_task(
    db: Session = Depends(get_db),
    provider: Provider = Depends(get_current_provider),
):
    """Get next task to execute"""
    
    # Find pending task that fits provider's resources
    task = db.query(Task).filter(
        Task.status == "pending",
        Task.provider_id == None,
    ).first()
    
    if not task:
        return {"task_id": None, "available": False}
    
    # Assign task to provider
    task.provider_id = provider.id
    task.status = "assigned"
    task.assigned_at = datetime.utcnow()
    
    db.commit()
    
    return {
        "task_id": str(task.id),
        "llm_model": task.llm_model,
        "prompt": task.prompt,
        "timeout_seconds": 300,
        "available": True,
    }


@router.post("/tasks/{task_id}/result", response_model=dict)
def submit_task_result(
    task_id: str,
    request: TaskResultSubmitRequest,
    db: Session = Depends(get_db),
    provider: Provider = Depends(get_current_provider),
):
    """Provider submits task result"""
    
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    if task.provider_id != provider.id:
        raise HTTPException(status_code=403, detail="Not assigned to this provider")
    
    # Update task
    task.status = "completed"
    task.result = request.result
    task.completion_time = request.execution_time_seconds
    task.completed_at = datetime.utcnow()
    
    # Calculate provider earnings
    earnings_credits = task.simulated_cost_credits
    
    # Award credits to provider
    provider.total_tasks_completed += 1
    provider.reputation_score = min(100, provider.reputation_score + 1)
    
    user_credits = db.query(UserCredits).filter(
        UserCredits.user_id == provider.user_id
    ).first()
    user_credits.virtual_credits += earnings_credits
    
    # Log transaction
    ledger = CreditLedger(
        user_id=provider.user_id,
        amount=earnings_credits,
        balance_after=user_credits.virtual_credits,
        transaction_type="task_completion",
    )
    db.add(ledger)
    
    db.commit()
    
    return {
        "status": "accepted",
        "earnings_credits": earnings_credits,
        "total_earned": earnings_credits,  # Simplified
        "new_reputation": provider.reputation_score,
    }


@router.get("/earnings", response_model=ProviderEarningsResponse)
def get_provider_earnings(
    db: Session = Depends(get_db),
    provider: Provider = Depends(get_current_provider),
):
    """Get provider earnings summary"""
    
    # Get user credits
    user_credits = db.query(UserCredits).filter(
        UserCredits.user_id == provider.user_id
    ).first()
    
    # Get earnings from last 30 days
    thirty_days_ago = datetime.utcnow() - timedelta(days=30)
    recent_earnings = db.query(CreditLedger).filter(
        CreditLedger.user_id == provider.user_id,
        CreditLedger.transaction_type == "task_completion",
        CreditLedger.created_at >= thirty_days_ago,
    ).all()
    
    total_earned_30d = sum(e.amount for e in recent_earnings)
    
    return ProviderEarningsResponse(
        provider_id=str(provider.id),
        total_credits_earned=total_earned_30d,
        current_balance=user_credits.virtual_credits,
        tasks_completed=provider.total_tasks_completed,
        reputation_score=provider.reputation_score,
    )
