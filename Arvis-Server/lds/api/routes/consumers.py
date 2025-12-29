"""Consumer API endpoints"""

from fastapi import APIRouter, Depends, HTTPException, Header
from sqlalchemy.orm import Session
import uuid

from lds.config.database import get_db
from lds.models.schemas import (
    TaskSubmitRequest,
    TaskSubmitResponse,
    TaskStatusResponse,
    AccountBalanceResponse,
    TransactionHistoryResponse,
)
from lds.models.database import Task, User, UserCredits, CreditLedger
from lds.services.security import verify_token
from lds.services.validators import InputValidator, RateLimiter
from datetime import datetime

router = APIRouter(prefix="/tasks", tags=["tasks"])


def get_current_user(
    authorization: str = Header(None),
    db: Session = Depends(get_db),
):
    """Get current user from API key"""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing API key")
    
    api_key = authorization.replace("Bearer ", "")
    
    user = db.query(User).filter(User.api_key == api_key).first()
    if not user:
        raise HTTPException(status_code=401, detail="Invalid API key")
    
    return user


@router.post("/submit", response_model=TaskSubmitResponse)
def submit_task(
    request: TaskSubmitRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Submit task for processing"""
    
    # Rate limiting (to be implemented with Redis connection from app context)
    # if not rate_limiter.check_rate_limit(str(user.id), "task_submission"):
    #     raise HTTPException(status_code=429, detail="Too many requests")
    
    # Validate input
    validator = InputValidator()
    is_valid, error_msg = validator.validate_prompt(request.prompt)
    if not is_valid:
        raise HTTPException(status_code=400, detail=error_msg)
    
    is_valid, error_msg = validator.validate_model(request.model)
    if not is_valid:
        raise HTTPException(status_code=400, detail=error_msg)
    
    # Calculate cost
    cost = validator.calculate_task_cost(
        request.model,
        len(request.prompt),
        request.timeout_seconds or 300,
    )
    
    # Check user has enough credits
    user_credits = db.query(UserCredits).filter(
        UserCredits.user_id == user.id
    ).first()
    
    if user_credits.virtual_credits < cost:
        raise HTTPException(status_code=402, detail="Insufficient credits")
    
    # Deduct credits
    user_credits.virtual_credits -= cost
    
    # Create task
    task = Task(
        id=str(uuid.uuid4()),
        consumer_id=user.id,
        status="pending",
        priority=request.priority or "normal",
        llm_model=request.model,
        prompt=request.prompt,
        simulated_cost_credits=cost,
    )
    db.add(task)
    
    # Log transaction
    ledger = CreditLedger(
        user_id=user.id,
        amount=-cost,
        balance_after=user_credits.virtual_credits,
        transaction_type="task_submission",
    )
    db.add(ledger)
    
    db.commit()
    
    return TaskSubmitResponse(
        task_id=task.id,
        status="queued",
        simulated_cost_credits=cost,
        estimated_wait_seconds=30,  # Simplified
        message="Task queued successfully",
    )


@router.get("/{task_id}", response_model=TaskStatusResponse)
def get_task_status(
    task_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Get task status"""
    
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    if task.consumer_id != user.id:
        raise HTTPException(status_code=403, detail="Not your task")
    
    return TaskStatusResponse(
        task_id=task.id,
        status=task.status,
        result=task.result,
        error_message=task.error_message,
        completion_time_seconds=task.completion_time,
    )


@router.get("/account/balance", response_model=AccountBalanceResponse)
def get_account_balance(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Get account balance"""
    
    user_credits = db.query(UserCredits).filter(
        UserCredits.user_id == user.id
    ).first()
    
    # Check if due for daily bonus
    today = datetime.utcnow().date()
    next_bonus = None
    if user_credits.last_daily_bonus:
        from datetime import timedelta
        next_bonus = user_credits.last_daily_bonus + timedelta(days=1)
    
    return AccountBalanceResponse(
        virtual_credits=user_credits.virtual_credits,
        next_daily_bonus_at=next_bonus,
        daily_bonus_amount=100,  # From settings
        message="Account balance retrieved successfully",
    )


@router.get("/account/transactions", response_model=TransactionHistoryResponse)
def get_transaction_history(
    limit: int = 50,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Get transaction history"""
    
    transactions = db.query(CreditLedger).filter(
        CreditLedger.user_id == user.id,
    ).order_by(CreditLedger.created_at.desc()).limit(limit).all()
    
    records = [
        {
            "timestamp": t.created_at.isoformat(),
            "type": t.transaction_type,
            "amount": t.amount,
            "balance_after": t.balance_after,
        }
        for t in transactions
    ]
    
    return TransactionHistoryResponse(
        user_id=str(user.id),
        total_transactions=len(records),
        records=records,
    )
