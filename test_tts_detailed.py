#!/usr/bin/env python
"""Detailed TTS subprocess test with logging"""

import sys
import subprocess
import os
from pathlib import Path
import logging

# Setup logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Test the subprocess worker
workspace_root = Path(__file__).parent / "Arvis-Client"
worker_path = workspace_root / "modules" / "tts_worker_subprocess.py"
output_file = Path.home() / "AppData" / "Local" / "Temp" / "test_tts_detailed.wav"
output_file.parent.mkdir(parents=True, exist_ok=True)

if not worker_path.exists():
    logger.error(f"Worker not found: {worker_path}")
    sys.exit(1)

venv_python = workspace_root / "venv" / "Scripts" / "python.exe"
if not venv_python.exists():
    logger.warning(f"venv python not found at {venv_python}, using system python")
    venv_python = sys.executable
else:
    logger.info(f"Using venv python: {venv_python}")

args = [
    str(venv_python),
    str(worker_path),
    "--text",
    "Привет, это тест синтеза речи Silero",
    "--voice",
    "aidar",
    "--sample-rate",
    "48000",
    "--device",
    "cpu",
    "--output",
    str(output_file),
    "--sapi-enabled",
]

logger.info(f"Command: {' '.join(args[:5])}...")
logger.info(f"Output file: {output_file}")
logger.info(f"Timeout: 45 seconds")

try:
    result = subprocess.run(
        args,
        capture_output=True,
        text=True,
        timeout=45,
        creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
    )
    
    logger.info(f"Return code: {result.returncode}")
    
    if result.stdout:
        logger.info(f"STDOUT:\n{result.stdout}")
    if result.stderr:
        logger.error(f"STDERR:\n{result.stderr}")
    
    if output_file.exists():
        size = output_file.stat().st_size
        logger.info(f"✓ Output file created: {size} bytes")
    else:
        logger.error(f"✗ Output file NOT created: {output_file}")
        
except subprocess.TimeoutExpired:
    logger.error("✗ TIMEOUT (45 seconds) - subprocess appears to be hanging")
    sys.exit(1)
except Exception as e:
    logger.error(f"✗ Error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
