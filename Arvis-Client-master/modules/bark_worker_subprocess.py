"""
Subprocess worker for Bark TTS.

This isolates heavy Bark/PyTorch imports from the main application process
and reduces the risk of DLL loading issues (e.g., c10.dll) crashing the UI.

Usage: invoked by BarkTTSEngine via Python subprocess.
Reads text from stdin by default; can also accept --text.
If --output is omitted, plays audio directly.
"""

from __future__ import annotations

import argparse
import sys
import os
import io
import json
from typing import Optional
import subprocess


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Bark TTS subprocess worker")
    p.add_argument("--text", type=str, default=None, help="Text to synthesize; if omitted, read from stdin")
    p.add_argument("--voice", type=str, default="v2/multilingual_00", help="Bark voice preset/history prompt")
    p.add_argument("--sample-rate", type=int, default=24000, help="Sample rate for playback/output")
    p.add_argument("--device", type=str, default="cpu", help="Device to use (cpu/cuda)")
    p.add_argument("--output", type=str, default=None, help="Optional output WAV filepath; if omitted, audio is played")
    return p.parse_args()


def read_text_from_stdin() -> str:
    try:
        data = sys.stdin.read()
        return data.strip()
    except Exception:
        return ""


def main() -> int:
    args = parse_args()
    text = (args.text or read_text_from_stdin() or "").strip()
    if not text:
        print("No text provided to Bark worker", file=sys.stderr)
        return 2

    # Try import Bark and dependencies in the worker only
    try:
        # Import bark-ml
        import numpy as np  # noqa: F401
        import bark  # type: ignore
        from bark import generate_audio  # type: ignore
    except Exception as e:
        # Attempt auto-install if allowed
        auto = os.environ.get("ARVIS_BARK_AUTOINSTALL", "1") == "1"
        if auto:
            try:
                print("[bark-worker] Attempting auto-install of Bark dependencies...", file=sys.stderr)
                subprocess.run([sys.executable, "-m", "pip", "install", "--upgrade", "pip"], check=False)
                # Prefer CPU wheels for Torch
                subprocess.run([
                    sys.executable, "-m", "pip", "install",
                    "--index-url", "https://download.pytorch.org/whl/cpu",
                    "torch", "torchvision", "torchaudio"
                ], check=False)
                subprocess.run([sys.executable, "-m", "pip", "install", "bark-ml", "sounddevice", "soundfile"], check=False)
                # Retry import
                import numpy as np  # type: ignore  # noqa: F401
                import bark  # type: ignore
                from bark import generate_audio  # type: ignore
            except Exception as e2:
                print(f"Bark auto-install failed: {e2}", file=sys.stderr)
                return 3
        else:
            # Common failure: Torch DLLs missing (c10.dll) or bark not installed
            print(f"Bark import error: {e}", file=sys.stderr)
            return 3

    # Synthesize
    try:
        voice = args.voice
        # generate_audio returns a numpy array of float32
        audio = generate_audio(text, history_prompt=voice, text_temp=0.7, waveform_temp=0.7)
        if audio is None:
            print("Bark returned no audio", file=sys.stderr)
            return 4

        # Output to WAV or playback
        if args.output:
            try:
                import soundfile as sf  # type: ignore
                sf.write(args.output, audio, samplerate=int(args.sample_rate))
                print(json.dumps({"status": "ok", "output": args.output}))
                return 0
            except Exception as e:
                print(f"Failed to write WAV: {e}", file=sys.stderr)
                return 5
        else:
            try:
                import sounddevice as sd  # type: ignore
                sd.play(audio, samplerate=int(args.sample_rate))
                sd.wait()
                print(json.dumps({"status": "ok", "played": True}))
                return 0
            except Exception as e:
                print(f"Playback failed: {e}", file=sys.stderr)
                return 6

    except Exception as e:
        print(f"Bark synthesis error: {e}", file=sys.stderr)
        return 7


if __name__ == "__main__":
    sys.exit(main())
