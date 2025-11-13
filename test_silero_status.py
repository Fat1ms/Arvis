"""Verify Silero model download complete and working"""
import sys
from pathlib import Path

# Check model cache
cache_dir = Path.home() / ".cache" / "torch" / "hub" / "snakers4_silero-models_master"
model_file = cache_dir / "src" / "silero" / "model" / "v3_1_ru.pt"

print(f"Cache dir exists: {cache_dir.exists()}")
print(f"Model file exists: {model_file.exists()}")

if model_file.exists():
    size_mb = model_file.stat().st_size / (1024*1024)
    print(f"Model size: {size_mb:.1f} MB")
    if size_mb > 100:
        print("Model appears complete (>100 MB)")
    else:
        print("WARNING: Model might be incomplete (<100 MB)")
else:
    print("Model file not found - will download on first use")

# Try loading
print("\nAttempting to load Silero...")
try:
    import torch
    model, _ = torch.hub.load(
        repo_or_dir='snakers4/silero-models',
        model='silero_tts',
        language='ru',
        speaker='v3_1_ru',
        verbose=False,
        trust_repo=True
    )
    print("SUCCESS: Silero model loaded")
    
    # Try synthesis
    audio = model.apply_tts(text="Привет", speaker="aidar", sample_rate=48000)
    print(f"Audio generated: {len(audio)} samples")
    
except Exception as e:
    print(f"ERROR: {e}")
