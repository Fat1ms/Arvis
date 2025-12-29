"""Rate limiting and input validation services"""

import logging
import re
from typing import Optional
from redis import Redis

from ..config.settings import settings

logger = logging.getLogger(__name__)


class RateLimiter:
    """Redis-based rate limiter"""
    
    def __init__(self, redis_client: Redis):
        self.redis = redis_client
    
    async def check_rate_limit(self, user_id: str, action: str = "tasks") -> bool:
        """
        Check if user has exceeded rate limit
        Returns: True if allowed, False if rate limited
        """
        try:
            key = f"ratelimit:{user_id}:{action}"
            current = self.redis.get(key)
            
            if current is None:
                # First request in this minute
                self.redis.setex(key, 60, 1)
                return True
            
            count = int(current)
            
            if action == "tasks" and count >= settings.RATE_LIMIT_TASKS_PER_MINUTE:
                return False
            
            # Increment counter
            self.redis.incr(key)
            return True
            
        except Exception as e:
            logger.error(f"Rate limit check failed: {e}")
            return True  # Allow on error (fail-open)


class InputValidator:
    """Input validation utilities"""
    
    # Blacklist patterns for prompt security
    BLACKLIST_PATTERNS = [
        r"rm\s+-rf",
        r"fork\s*\(\s*\)",
        r"exec\s*\(",
        r"system\s*\(",
        r"__import__",
        r"eval\s*\(",
        r"pickle",
        r"subprocess",
        r"os\.system",
    ]
    
    @staticmethod
    def validate_prompt(prompt: str) -> tuple[bool, Optional[str]]:
        """
        Validate prompt for suspicious content
        Returns: (is_valid, error_message)
        """
        # Check length
        if len(prompt) > settings.TASK_MAX_PROMPT_LENGTH:
            return False, f"Prompt too long (max {settings.TASK_MAX_PROMPT_LENGTH} chars)"
        
        if len(prompt) < 1:
            return False, "Prompt cannot be empty"
        
        # Check for blacklist patterns
        prompt_lower = prompt.lower()
        for pattern in InputValidator.BLACKLIST_PATTERNS:
            if re.search(pattern, prompt_lower):
                return False, f"Suspicious content detected in prompt"
        
        return True, None
    
    @staticmethod
    def validate_model(model: str) -> tuple[bool, Optional[str]]:
        """
        Validate model name against whitelist
        Returns: (is_valid, error_message)
        """
        allowed_models = settings.get_allowed_models()
        if model not in allowed_models:
            allowed = ", ".join(allowed_models)
            return False, f"Model not allowed. Allowed models: {allowed}"
        
        return True, None
    
    @staticmethod
    def calculate_task_cost(model: str, prompt_length: int, timeout: int = 300) -> int:
        """Calculate virtual credit cost for task"""
        model_costs = settings.get_model_costs()
        base_cost = model_costs.get(model, 50)
        
        # Adjust for prompt length (max 10% increase)
        length_factor = min(1.1, 1.0 + (prompt_length / 100000))
        
        # Adjust for timeout (priority)
        timeout_factor = 1.0
        if timeout < 60:
            timeout_factor = 1.5  # Urgent
        elif timeout > 300:
            timeout_factor = 0.8  # Batch
        
        cost = int(base_cost * length_factor * timeout_factor)
        return cost
