#!/usr/bin/env python
"""Quick TTS subprocess test"""

import sys
import subprocess
import os
from pathlib import Path

# Test the subprocess worker
worker_path = Path(__file__).parent / "Arvis-Client" / "modules" / "tts_worker_subprocess.py"
output_file = Path.home() / "AppData" / "Local" / "Temp" / "test_tts_output.wav"

if not worker_path.exists():
    print(f"Worker not found: {worker_path}")
    sys.exit(1)

venv_python = Path(__file__).parent / "Arvis-Client" / "venv" / "Scripts" / "python.exe"
if not venv_python.exists():
    venv_python = sys.executable

text_to_speak = "Привет, это тест синтеза речи Silero"
args = [
    str(venv_python),
    str(worker_path),
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

print(f"Running: {' '.join(args[:5])}...")
print(f"Output file: {output_file}")

try:
    result = subprocess.run(
        [str(arg) for arg in args],
        input=text_to_speak,
        capture_output=True,
        timeout=30,
        creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
        check=True,
        encoding='utf-8'
    )
    
    print(f"\nReturn code: {result.returncode}")
    print(f"\nSTDOUT:\n{result.stdout}")
    if result.stderr:
        print(f"\nSTDERR:\n{result.stderr}")
    
    if output_file.exists():
        size = output_file.stat().st_size
        print(f"\n✓ Output file created: {size} bytes")
    else:
        print("\n✗ Output file NOT created")
        
except subprocess.CalledProcessError as e:
    print(f"✗ ERROR: Subprocess failed with exit code {e.returncode}")
    print(f"\nSTDOUT:\n{e.stdout}")
    print(f"\nSTDERR:\n{e.stderr}")
    sys.exit(1)
except subprocess.TimeoutExpired:
    print("✗ TIMEOUT (30 seconds)")
    sys.exit(1)
except Exception as e:
    print(f"✗ Error: {e}")
    sys.exit(1)
