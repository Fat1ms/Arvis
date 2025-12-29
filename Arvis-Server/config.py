"""
Server Configuration Management
Управление конфигурацией сервера
"""

import os
from pathlib import Path
from typing import List

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables"""

    # Server
    server_host: str = "0.0.0.0"
    server_port: int = 8000
    server_reload: bool = False
    server_workers: int = 4

    # Security
    secret_key: str = "dev-secret-key-change-in-production"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 60
    refresh_token_expire_days: int = 30

    # Database
    database_url: str = "sqlite:///./data/auth_server.db"

    # CORS
    allowed_origins: str = "http://localhost:*,https://localhost:*"
    cors_allow_credentials: bool = True

    # Rate Limiting
    rate_limit_max_requests: int = 100
    rate_limit_window_seconds: int = 60

    # Session
    session_timeout_minutes: int = 60
    max_sessions_per_user: int = 5

    # Login Security
    max_login_attempts: int = 5
    lockout_duration_minutes: int = 15
    password_min_length: int = 8

    # Logging
    log_level: str = "INFO"
    log_file: str = "logs/auth_server.log"
    log_max_size_mb: int = 10
    log_backup_count: int = 5

    # Guest Mode
    guest_session_duration_minutes: int = 30
    guest_enabled: bool = True

    # 2FA
    totp_issuer: str = "Arvis"
    totp_enabled: bool = True

    # Admin Account
    admin_username: str = "admin"
    admin_password: str = "ChangeMeOnFirstRun123!"
    admin_email: str = "admin@arvis.local"

    # External APIs (server-side protected)
    openweather_api_key: str = ""
    openweather_base_url: str = "https://api.openweathermap.org/data/2.5"
    weather_cache_ttl_minutes: int = 15

    newsapi_api_key: str = ""
    newsapi_base_url: str = "https://newsapi.org/v2"
    news_cache_ttl_minutes: int = 30

    # Billing (Payments)
    billing_enabled: bool = False

    public_base_url: str = "http://localhost:8000"  # used to build return/webhook urls

    stripe_secret_key: str = ""
    stripe_webhook_secret: str = ""

    # LiqPay
    liqpay_public_key: str = ""
    liqpay_private_key: str = ""

    # Product defaults (MVP)
    billing_product_key: str = "arvis_local"
    billing_product_name: str = "Arvis"
    billing_currency: str = "EUR"
    billing_one_time_amount_cents: int = 0
    billing_subscription_amount_cents: int = 0

    # Downloads
    downloads_enabled: bool = True
    downloads_token_ttl_seconds: int = 15 * 60
    downloads_asset_key_windows: str = "arvis_windows_exe"
    downloads_windows_exe_path: str = ""  # absolute or relative path to the .exe file
    downloads_windows_exe_filename: str = "Arvis.exe"
    downloads_windows_exe_version: str = ""

    class Config:
        env_file = ".env"
        case_sensitive = False
        extra = "ignore"

    @property
    def allowed_origins_list(self) -> List[str]:
        """Parse allowed origins from comma-separated string"""
        return [origin.strip() for origin in self.allowed_origins.split(",")]

    @property
    def is_production(self) -> bool:
        """Check if running in production mode"""
        return not self.server_reload and self.secret_key != "dev-secret-key-change-in-production"


# Global settings instance
settings = Settings()


def get_settings() -> Settings:
    """Get application settings"""
    return settings


# Ensure directories exist
def init_directories():
    """Initialize required directories"""
    directories = [
        Path("data"),
        Path("logs"),
        Path("logs/audit"),
        Path("downloads"),
    ]

    for directory in directories:
        directory.mkdir(parents=True, exist_ok=True)


# Initialize on module load
init_directories()
