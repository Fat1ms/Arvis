#!/usr/bin/env python
"""Test torch import in subprocess"""

import sys
import os

print("[TEST] Subprocess started", file=sys.stderr, flush=True)

try:
    print("[TEST] Attempting torch import...", file=sys.stderr, flush=True)
    import torch as _torch
    print(f"[TEST] Torch imported successfully: {_torch.__version__}", file=sys.stderr, flush=True)
    
    print("[TEST] Checking CUDA availability...", file=sys.stderr, flush=True)
    cuda_available = _torch.cuda.is_available()
    print(f"[TEST] CUDA available: {cuda_available}", file=sys.stderr, flush=True)
    
    print("[TEST] Attempting torch.hub.load...", file=sys.stderr, flush=True)
    loaded = _torch.hub.load(
        repo_or_dir="snakers4/silero-models",
        model="silero_tts",
        language="ru",
        speaker="v3_1_ru",
        verbose=False,
    )
    print("[TEST] torch.hub.load completed", file=sys.stderr, flush=True)
    
    print("SUCCESS")
    
except Exception as e:
    print(f"[ERROR] {e}", file=sys.stderr, flush=True)
    import traceback
    traceback.print_exc(file=sys.stderr)
    sys.exit(1)
