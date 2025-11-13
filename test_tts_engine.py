#!/usr/bin/env python
"""Test SileroTTSEngine directly"""

import sys
from pathlib import Path

# Add project root to path
workspace_root = Path(__file__).parent / "Arvis-Client"
sys.path.insert(0, str(workspace_root))
sys.path.insert(0, str(workspace_root.parent))

from config.config import Config
from modules.silero_tts_engine import SileroTTSEngine
from utils.logger import ModuleLogger
import time

# Setup logger
logger = ModuleLogger("TestTTS")
logger.info("Starting TTS test...")

# Load config
try:
    config = Config(workspace_root / "config" / "config.json")
    logger.info(f"Config loaded")
except Exception as e:
    logger.error(f"Failed to load config: {e}")
    sys.exit(1)

# Create TTS engine
try:
    tts = SileroTTSEngine(config, logger)
    logger.info("SileroTTSEngine created")
except Exception as e:
    logger.error(f"Failed to create TTS engine: {e}")
    sys.exit(1)

# Test speak
try:
    logger.info("Testing speak()...")
    tts.speak("Привет, это тест синтеза речи Silero")
    logger.info("Speak() called, waiting for synthesis...")
    
    # Wait for async task to complete
    time.sleep(5)
    logger.info("Test complete")
    
except Exception as e:
    logger.error(f"Failed to test speak: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
