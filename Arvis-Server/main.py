"""
Arvis Authentication Server - Main Application
Главное приложение сервера аутентификации Arvis
"""

import hashlib
import logging
import secrets
import sys
import uuid
from contextlib import asynccontextmanager
from datetime import datetime
from logging.handlers import RotatingFileHandler
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from server.api import auth, users, weather, news, billing, downloads
from server.config import get_settings, init_directories
from server.database.models import RoleEnum, User
from server.database.storage import DatabaseStorage, SessionLocal, init_database
from server.version import get_full_server_info, check_client_compatibility, __server_version__

settings = get_settings()


# ==================== Logging Setup ====================


def setup_logging():
    """Setup logging configuration"""
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)

    # Create logger
    logger = logging.getLogger("arvis_auth_server")
    logger.setLevel(getattr(logging, settings.log_level.upper()))

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    console_handler.setFormatter(console_formatter)

    # File handler with rotation
    file_handler = RotatingFileHandler(
        settings.log_file,
        maxBytes=settings.log_max_size_mb * 1024 * 1024,
        backupCount=settings.log_backup_count,
        encoding="utf-8",
    )
    file_handler.setLevel(logging.DEBUG)
    file_formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s"
    )
    file_handler.setFormatter(file_formatter)

    # Add handlers
    logger.addHandler(console_handler)
    logger.addHandler(file_handler)

    return logger


logger = setup_logging()


# ==================== Database Initialization ====================


def init_admin_user():
    """Initialize default admin user"""
    import bcrypt
    
    db = SessionLocal()
    try:
        storage = DatabaseStorage(db)

        # Check if admin exists
        admin = storage.get_user_by_username(settings.admin_username)
        if admin:
            logger.info(f"Admin user '{settings.admin_username}' already exists")
            return

        # Create admin user with bcrypt hashing (using bcrypt directly)
        # Use shorter salt (8 bytes = 16 hex chars) to keep under 72 byte limit
        salt = secrets.token_hex(8)
        # Bcrypt has 72 byte limit, so truncate password+salt
        password_bytes = (settings.admin_password + salt).encode('utf-8')[:72]
        password_hash = bcrypt.hashpw(password_bytes, bcrypt.gensalt()).decode('utf-8')

        admin = User(
            user_id=str(uuid.uuid4()),
            username=settings.admin_username,
            email=settings.admin_email,
            password_hash=password_hash,
            salt=salt,
            role=RoleEnum.ADMIN,
            is_active=True,
            require_2fa=False,
        )

        storage.create_user(admin)
        logger.info(f"✓ Admin user '{settings.admin_username}' created successfully")
        logger.warning(f"⚠ Default admin password: {settings.admin_password}")
        logger.warning("⚠ Please change the admin password immediately!")

    except Exception as e:
        logger.error(f"Error creating admin user: {e}")
        raise
    finally:
        db.close()


# ==================== Lifecycle Management ====================


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events"""
    # Startup
    logger.info("=" * 80)
    logger.info("🚀 Starting Arvis Authentication Server")
    logger.info(f"Version: {__server_version__}")
    logger.info(f"Environment: {'Production' if settings.is_production else 'Development'}")
    logger.info("=" * 80)

    # Initialize directories and database
    init_directories()
    init_database()
    logger.info("✓ Database initialized")

    # Create admin user if not exists
    init_admin_user()

    logger.info(f"✓ Server listening on {settings.server_host}:{settings.server_port}")
    logger.info("✓ Authentication server ready!")

    yield

    # Shutdown
    logger.info("Shutting down Arvis Authentication Server...")


# ==================== FastAPI Application ====================


app = FastAPI(
    title="Arvis Authentication Server",
    description="""
    Centralized authentication server for Arvis AI Assistant
    
    ## Authentication
    
    1. **Login**: Use `/api/auth/login` endpoint with username and password
    2. **Get Token**: Copy the `access_token` from the response
    3. **Authorize**: Click the 🔒 **Authorize** button (top right)
    4. **Enter Token**: Paste the token in the format: `Bearer YOUR_TOKEN_HERE`
    5. **Test**: Now you can use protected endpoints!
    
    ### Default Admin Credentials:
    - **Username**: `admin`
    - **Password**: `ChangeMeOnFirstRun123!`
    
    ⚠️ **Important**: Change the default password after first login!
    """,
    version=__server_version__,
    lifespan=lifespan,
    docs_url="/docs" if not settings.is_production else None,
    redoc_url="/redoc" if not settings.is_production else None,
)


# ==================== Middleware ====================


# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins_list,
    allow_credentials=settings.cors_allow_credentials,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Request logging middleware
@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log all requests"""
    start_time = datetime.now()

    # Process request
    response = await call_next(request)

    # Calculate duration
    duration = (datetime.now() - start_time).total_seconds()

    # Log request
    logger.info(
        f"{request.method} {request.url.path} - "
        f"Status: {response.status_code} - "
        f"Duration: {duration:.3f}s - "
        f"Client: {request.client.host if request.client else 'unknown'}"
    )

    return response


# ==================== Exception Handlers ====================


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler"""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)

    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "message": str(exc) if not settings.is_production else "An unexpected error occurred",
        },
    )


# ==================== Routes ====================


# Include routers
app.include_router(auth.router)
app.include_router(users.router)
app.include_router(weather.router)
app.include_router(news.router)
app.include_router(billing.router)
app.include_router(downloads.router)

# Minimal website (static HTML + JS)
web_dir = Path(__file__).parent / "web"
if web_dir.exists():
    app.mount("/web", StaticFiles(directory=str(web_dir), html=True), name="web")


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "service": "Arvis Authentication Server",
        "version": __server_version__,
        "status": "running",
        "timestamp": datetime.utcnow().isoformat(),
    }


@app.get("/health")
async def health():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "database": "connected",
    }


@app.get("/version", tags=["System"])
async def version_info():
    """
    Get server version information
    
    Returns version, API version, and minimum client requirements.
    No authentication required.
    """
    return get_full_server_info()


@app.get("/version/check", tags=["System"])
async def check_version(client_version: str):
    """
    Check client version compatibility
    
    Verifies if the client version is compatible with the server.
    No authentication required.
    """
    is_compatible, message = check_client_compatibility(client_version)
    return {
        "compatible": is_compatible,
        "message": message,
        "server_version": __server_version__,
        "client_version": client_version,
    }


@app.get("/test", tags=["Testing"])
async def test_endpoint():
    """
    Simple test endpoint
    
    Returns a simple response to verify the server is working.
    No authentication required - perfect for testing!
    """
    return {
        "message": "Server is working!",
        "status": "ok",
        "timestamp": datetime.utcnow().isoformat(),
        "version": __server_version__,
        "tip": "To test authentication, login at /api/auth/login and use the token in Authorize button"
    }


# ==================== Main Entry Point ====================


def main():
    """Main entry point"""
    import uvicorn

    logger.info("Starting server with uvicorn...")

    uvicorn.run(
        "server.main:app",
        host=settings.server_host,
        port=settings.server_port,
        reload=settings.server_reload,
        workers=1 if settings.server_reload else settings.server_workers,
        log_level=settings.log_level.lower(),
        access_log=True,
    )


if __name__ == "__main__":
    main()
