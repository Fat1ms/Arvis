import os
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Configuration settings for LDS API"""
    
    # Application
    APP_NAME: str = "Arvis LDS API"
    APP_VERSION: str = "0.1.0"
    DEBUG: bool = os.getenv("DEBUG", "false").lower() == "true"
    
    # Server
    HOST: str = os.getenv("HOST", "0.0.0.0")
    PORT: int = int(os.getenv("PORT", "8000"))
    
    # Database
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL",
        "postgresql://user:password@localhost:5432/arvis_lds"
    )
    
    # Redis
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    
    # Security
    SECRET_KEY: str = os.getenv("SECRET_KEY", "dev-secret-key-change-in-production")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7 days
    
    # TLS
    USE_TLS: bool = os.getenv("USE_TLS", "true").lower() == "true"
    CERT_PATH: str = os.getenv("CERT_PATH", "/etc/letsencrypt/live/lds-api.arvis.cloud/fullchain.pem")
    KEY_PATH: str = os.getenv("KEY_PATH", "/etc/letsencrypt/live/lds-api.arvis.cloud/privkey.pem")
    
    # Rate Limiting
    RATE_LIMIT_TASKS_PER_MINUTE: int = 10  # Free tier
    RATE_LIMIT_GLOBAL_PER_SECOND: int = 100
    
    # Task Configuration
    TASK_TIMEOUT_SECONDS: int = 300  # 5 minutes
    TASK_MAX_PROMPT_LENGTH: int = 10000
    TASK_QUEUE_MAX_SIZE: int = 10000
    
    # Provider Configuration
    PROVIDER_HEARTBEAT_INTERVAL: int = 30  # seconds
    PROVIDER_HEARTBEAT_TIMEOUT: int = 120  # seconds
    
    # Credits (Virtual)
    SIGNUP_BONUS_CREDITS: int = 1000
    DAILY_BONUS_CREDITS: int = 100
    
    # Allowed Models
    ALLOWED_MODELS: str = "mistral:7b,gemma:2b,code-llama:34b"
    
    # Model Costs (Virtual Credits)
    MODEL_COST_MISTRAL_7B: int = 50
    MODEL_COST_GEMMA_2B: int = 20
    MODEL_COST_CODE_LLAMA_34B: int = 100
    
    def get_allowed_models(self) -> list[str]:
        """Parse comma-separated model list"""
        return [m.strip() for m in self.ALLOWED_MODELS.split(",")]
    
    def get_model_costs(self) -> dict[str, int]:
        """Get model costs as dictionary"""
        return {
            "mistral:7b": self.MODEL_COST_MISTRAL_7B,
            "gemma:2b": self.MODEL_COST_GEMMA_2B,
            "code-llama:34b": self.MODEL_COST_CODE_LLAMA_34B,
        }
    
    class Config:
        env_file = ".env"


settings = Settings()
