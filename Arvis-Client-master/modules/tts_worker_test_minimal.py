#!/usr/bin/env python
"""Minimal TTS subprocess to test if it even runs"""

import sys
import os

print("[TEST] Subprocess started!", file=sys.stderr)
print("[TEST] Python:", sys.executable, file=sys.stderr)
print("[TEST] Args:", sys.argv, file=sys.stderr)

try:
    print("[TEST] Importing argparse...", file=sys.stderr)
    import argparse
    
    print("[TEST] Parsing arguments...", file=sys.stderr)
    parser = argparse.ArgumentParser()
    parser.add_argument("--text", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    
    print(f"[TEST] Text: {args.text[:30]}", file=sys.stderr)
    print(f"[TEST] Output: {args.output}", file=sys.stderr)
    
    print("[TEST] Attempting soundfile import...", file=sys.stderr)
    import soundfile as sf
    print("[TEST] soundfile imported successfully", file=sys.stderr)
    
    print("[TEST] Creating dummy audio...", file=sys.stderr)
    import numpy as np
    audio = np.ones(48000, dtype=np.float32) * 0.1  # 1 second of silence
    
    print(f"[TEST] Writing to {args.output}...", file=sys.stderr)
    sf.write(args.output, audio, 48000)
    print(f"[TEST] File written successfully", file=sys.stderr)
    
    print("SUCCESS")
    
except Exception as e:
    print(f"[ERROR] {e}", file=sys.stderr)
    import traceback
    traceback.print_exc(file=sys.stderr)
    sys.exit(1)
