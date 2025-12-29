"""Task executor - runs in sandboxed Docker container"""

import os
import sys
import json
import logging
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def main():
    """Main executor entry point"""
    
    task_id = os.getenv("TASK_ID")
    task_timeout = int(os.getenv("TASK_TIMEOUT", "300"))
    
    logger.info(f"Executor started for task {task_id}")
    logger.info(f"Timeout: {task_timeout}s")
    logger.info(f"Resource limits enforced by cgroups")
    
    # In production: receive task from server via Redis/HTTP
    # For MVP: simulate task execution
    
    try:
        # Simulate LLM execution
        result = {
            "task_id": task_id,
            "status": "completed",
            "result": "This is a simulated LLM result. In production, this would be from Ollama.",
            "execution_time_seconds": 5.5,
            "tokens_generated": 150,
            "timestamp": datetime.utcnow().isoformat(),
        }
        
        # Output result as JSON
        print(json.dumps(result))
        logger.info(f"Task {task_id} completed successfully")
        
        sys.exit(0)
    
    except Exception as e:
        logger.error(f"Task execution failed: {e}")
        result = {
            "task_id": task_id,
            "status": "failed",
            "error": str(e),
        }
        print(json.dumps(result))
        sys.exit(1)


if __name__ == "__main__":
    main()
