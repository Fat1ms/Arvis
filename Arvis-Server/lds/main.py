"""Main FastAPI application"""

import logging
from contextlib import asynccontextmanager
from datetime import datetime

from fastapi import FastAPI, Depends, HTTPException, Header, status
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from redis import Redis

from .config.settings import settings
from .config.database import init_db, get_db
from .models.schemas import HealthCheckResponse, ErrorResponse, UserRegisterRequest, UserRegisterResponse
from .models.database import User, UserCredits, CreditLedger, Provider
from .services.security import hash_password, create_access_token
from .services.validators import RateLimiter, InputValidator
from .api.routes import providers, consumers

# Configure logging
logging.basicConfig(
    level=logging.DEBUG if settings.DEBUG else logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Redis connection
try:
    redis_client = Redis.from_url(settings.REDIS_URL, decode_responses=True)
    redis_client.ping()
    logger.info("Connected to Redis")
except Exception as e:
    logger.error(f"Failed to connect to Redis: {e}")
    redis_client = None

# Rate limiter
rate_limiter = RateLimiter(redis_client) if redis_client else None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events"""
    # Startup
    logger.info("Starting up LDS API...")
    try:
        await init_db()
    except Exception as e:
        logger.error(f"Database initialization failed: {e}")
    
    yield
    
    # Shutdown
    logger.info("Shutting down LDS API...")


# Create FastAPI app
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    debug=settings.DEBUG,
    lifespan=lifespan,
)

# Include routes
app.include_router(providers.router)
app.include_router(consumers.router)


# ============ Health Check ============

@app.get("/health", response_model=HealthCheckResponse)
async def health_check(db: Session = Depends(get_db)):
    """Health check endpoint"""
    from sqlalchemy import text
    
    try:
        # Check database
        db.execute(text("SELECT 1"))
        db_status = "healthy"
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        db_status = "unhealthy"
    
    try:
        # Check Redis
        if redis_client:
            redis_client.ping()
            redis_status = "healthy"
        else:
            redis_status = "not available"
    except Exception as e:
        logger.error(f"Redis health check failed: {e}")
        redis_status = "unhealthy"
    
    return HealthCheckResponse(
        status="healthy" if db_status == "healthy" else "degraded",
        version=settings.APP_VERSION,
        timestamp=datetime.utcnow(),
        database=db_status,
        redis=redis_status,
    )


# ============ Authentication ============

@app.post("/auth/register", response_model=UserRegisterResponse)
async def register(request: UserRegisterRequest, db: Session = Depends(get_db)):
    """Register new user (consumer or provider)"""
    try:
        # Check if user exists
        existing_user = db.query(User).filter(User.email == request.email).first()
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered"
            )
        
        # Create user
        import uuid
        import secrets
        
        user_id = str(uuid.uuid4())
        api_key = f"sk_{secrets.token_urlsafe(48)}"
        
        user = User(
            id=user_id,
            email=request.email,
            hashed_password=hash_password(request.password),
            api_key=api_key,
            role=request.role,
        )
        db.add(user)
        
        # Create Provider record if role is provider
        if request.role == "provider":
            provider = Provider(
                user_id=user_id,
                status="inactive",
                ram_allocated_gb=0,
                cpu_cores_allocated=0,
                gpu_allocated=0,
            )
            db.add(provider)
        
        # Create credits record
        credits = UserCredits(
            user_id=user_id,
            virtual_credits=settings.SIGNUP_BONUS_CREDITS,
        )
        db.add(credits)
        
        # Log in ledger
        ledger = CreditLedger(
            user_id=user_id,
            amount=settings.SIGNUP_BONUS_CREDITS,
            balance_after=settings.SIGNUP_BONUS_CREDITS,
            transaction_type="signup_bonus",
        )
        db.add(ledger)
        
        db.commit()
        
        logger.info(f"User registered: {user_id} ({request.email}) as {request.role}")
        
        return UserRegisterResponse(
            user_id=user_id,
            email=request.email,
            api_key=api_key,
            virtual_credits=settings.SIGNUP_BONUS_CREDITS,
            message=f"Welcome! You got {settings.SIGNUP_BONUS_CREDITS} virtual credits to start. MVP phase: everything is FREE!"
        )
    
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(e)
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Registration error: {e}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Registration failed"
        )


# ============ Error handling ============

@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    """Handle HTTP exceptions"""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "detail": exc.detail,
            "error_code": "HTTP_ERROR",
            "timestamp": datetime.utcnow().isoformat(),
        }
    )


@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    """Handle general exceptions"""
    logger.error(f"Unhandled exception: {exc}")
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=ErrorResponse(
            detail="Internal server error",
            error_code="INTERNAL_ERROR",
            timestamp=datetime.utcnow(),
        ).dict()
    )


if __name__ == "__main__":
    import uvicorn
    
    ssl_keyfile = None
    ssl_certfile = None
    
    if settings.USE_TLS:
        ssl_keyfile = settings.KEY_PATH
        ssl_certfile = settings.CERT_PATH
    
    uvicorn.run(
        "main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
        ssl_keyfile=ssl_keyfile,
        ssl_certfile=ssl_certfile,
    )
