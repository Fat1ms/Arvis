"""
Subprocess TTS worker to synthesize and play speech using Silero TTS
This isolates Silero's 'src' imports from the main app's packages.
"""

import argparse
import os
import sys
from pathlib import Path
from typing import Any

import contextlib
import io
import shutil
import warnings
import re

import soundfile as sf


def ensure_silero_paths() -> None:
    """Adjust sys.path to prefer Silero repo paths over project paths."""
    # Remove current working directory and project src from sys.path to avoid 'src' name clash
    cwd = os.path.abspath(os.getcwd())
    sys.path = [p for p in sys.path if os.path.abspath(p) not in (cwd, os.path.join(cwd, "src"))]

    # Try to locate torch hub cache of silero repo
    repo_root = Path.home() / ".cache" / "torch" / "hub" / "snakers4_silero-models_master"
    if repo_root.exists():
        repo_src = repo_root / "src"
        # Prepend repo paths
        sys.path.insert(0, str(repo_root))
        sys.path.insert(0, str(repo_src))

def map_voice(voice: str) -> str:
    # Provide a safe default mapping if a generic voice is passed
    if not voice:
        return "aidar"
    v = voice.lower().strip()
    if v in {"ru_v3", "ru-v3", "v3", "default"}:
        return "aidar"
    return voice

def preprocess_text(text: str) -> str:
    """Clean and normalize input text for Silero to avoid ValueError from tokenizer.

    - Trim whitespace
    - Remove/replace unsupported characters
    - Collapse whitespace
    - Ensure sentence-ending punctuation
    - Limit overly long inputs to a safe length
    """
    if text is None:
        return ""
    t = text.strip()
    if not t:
        return ""
    # Replace unsupported chars with space; allow russian/latin letters, digits and common punctuation
    t = re.sub(r"[^0-9A-Za-zА-Яа-яёЁ ,.!?;:\-()\"'–—]", " ", t)
    # Normalize dashes
    t = t.replace("–", "-").replace("—", "-")
    # Collapse whitespace
    t = re.sub(r"\s+", " ", t)
    t = t.strip()
    # Ensure it ends with punctuation to mark sentence end
    if t and t[-1] not in ".!?":
        t += "."
    # Limit length to avoid extreme inputs
    if len(t) > 5000:
        t = t[:5000]
    return t

def synth_and_play(
    text: str,
    voice: str,
    sample_rate: int,
    device: str,
    output: str | None,
    sapi_enabled: bool = True,
) -> None:
    print("[TTS-WORKER] Starting synth_and_play...", file=sys.stderr)

    # Optional torch import to avoid DLL crashes
    try:
        print("[TTS-WORKER] Importing torch...", file=sys.stderr)
        import torch as _torch  # type: ignore
        _torch_err = None
        print("[TTS-WORKER] torch imported successfully.", file=sys.stderr)
    except BaseException as _e:
        _torch = None  # type: ignore
        _torch_err = _e
        print(f"[TTS-WORKER-ERROR] torch import failed: {_e}", file=sys.stderr)

    # Подавляем предупреждения PyTorch для чистого вывода
    warnings.filterwarnings("ignore", category=UserWarning)
    warnings.filterwarnings("ignore", category=FutureWarning)

    # Make sure silero repo is importable
    print("[TTS-WORKER] Ensuring Silero paths...", file=sys.stderr)
    ensure_silero_paths()

    # Устанавливаем переменные окружения для подавления лишнего вывода
    os.environ["TOKENIZERS_PARALLELISM"] = "false"

    # torch обязателен для Silero
    if _torch is None:
        raise RuntimeError(f"PyTorch not available: {_torch_err}")

    def _clear_silero_cache(torch_mod: Any) -> None:
        """Удаляем поврежденный кеш Silero из torch.hub (репо и возможные .pt чекпоинты)."""
        try:
            try:
                hub_dir = Path(torch_mod.hub.get_dir())  # type: ignore[attr-defined]
            except Exception:
                hub_dir = Path.home() / ".cache" / "torch" / "hub"

            targets: list[Path] = []
            repo_dir = hub_dir / "snakers4_silero-models_master"
            targets.append(repo_dir)
            checkpoints = hub_dir / "checkpoints"
            if checkpoints.exists():
                for p in checkpoints.glob("*.pt"):
                    name = p.name.lower()
                    if "silero" in name or "v3" in name or "ru" in name:
                        targets.append(p)
            for t in targets:
                if t.exists():
                    if t.is_dir():
                        shutil.rmtree(t, ignore_errors=True)
                        print(f"[TTS-WORKER] Cleared dir: {t}", file=sys.stderr)
                    else:
                        try:
                            t.unlink(missing_ok=True)
                        except TypeError:
                            # Python <3.8 fallback
                            try:
                                t.unlink()
                            except Exception:
                                pass
                        print(f"[TTS-WORKER] Removed file: {t}", file=sys.stderr)
        except Exception as clr_err:
            print(f"[TTS-WORKER-WARN] Failed to clear silero cache: {clr_err}", file=sys.stderr)

    def _load_model() -> Any:
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
            loaded = _torch.hub.load(  # type: ignore[attr-defined]
                repo_or_dir="snakers4/silero-models",
                model="silero_tts",
                language="ru",
                speaker="v3_1_ru",
                verbose=False,
            )
        return loaded[0] if isinstance(loaded, (tuple, list)) else loaded

    try:
        print("[TTS-WORKER] Starting synthesis...", file=sys.stderr)
        print("[TTS-WORKER] Loading Silero model...", file=sys.stderr)
        try:
            model = _load_model()
        except Exception as load_err:
            msg = str(load_err)
            if (
                "PytorchStreamReader failed" in msg
                or "failed finding central directory" in msg
                or "zip archive" in msg
            ):
                print("[TTS-WORKER] Detected corrupted Silero cache, clearing and retrying...", file=sys.stderr)
                _clear_silero_cache(_torch)
                model = _load_model()
            else:
                raise

        print("[TTS-WORKER] Silero model loaded.", file=sys.stderr)
        print("[TTS-WORKER] Model loaded, preparing...", file=sys.stderr)

        # Безопасно выбираем устройство: если cuda недоступна, откатываемся на cpu
        target_device = device
        try:
            if (
                isinstance(target_device, str)
                and target_device.lower().startswith("cuda")
                and not _torch.cuda.is_available()
            ):
                target_device = "cpu"
        except Exception:
            target_device = "cpu"

        print(f"[TTS-WORKER] Moving model to device: {target_device}", file=sys.stderr)
        model_any: Any = model
        model_any.to(target_device)
        print("[TTS-WORKER] Model moved to device.", file=sys.stderr)

        voice_mapped = map_voice(voice)
        print(f"[TTS-WORKER] Generating audio with voice '{voice_mapped}'...", file=sys.stderr)
        # Preprocess text to avoid Silero ValueError on unexpected symbols or empty input
        clean_text = preprocess_text(text)
        if not clean_text:
            print("[TTS-WORKER-WARN] Input reduced to empty after preprocessing; using safe fallback.", file=sys.stderr)
            clean_text = "Привет."
        print(f"[TTS-WORKER] Clean text: {clean_text}", file=sys.stderr)
        buf = io.StringIO()
        try:
            with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
                audio = model_any.apply_tts(
                    text=clean_text,
                    speaker=voice_mapped,
                    sample_rate=sample_rate,
                    put_accent=True,
                    put_yo=True,
                )
        except ValueError:
            # Retry with a minimal safe sample to verify pipeline
            retry_text = "Привет."
            print("[TTS-WORKER-WARN] ValueError for input text; retrying with a safe sample...", file=sys.stderr)
            with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
                audio = model_any.apply_tts(
                    text=retry_text,
                    speaker=voice_mapped,
                    sample_rate=sample_rate,
                    put_accent=True,
                    put_yo=True,
                )
        print("[TTS-WORKER] Audio generated.", file=sys.stderr)

        print("[TTS-WORKER] Audio generated, saving...", file=sys.stderr)
        # Convert to numpy array
        if hasattr(_torch, "is_tensor") and _torch.is_tensor(audio):
            audio = audio.cpu().numpy()

        if output:
            print(f"[TTS-WORKER] Writing to output file: {output}", file=sys.stderr)
            sf.write(output, audio, sample_rate)
            print(f"Audio saved to: {output}")
            print("[TTS-WORKER] Finished writing to output file.", file=sys.stderr)
        else:
            print("[TTS-WORKER] No output file specified; playing audio via sounddevice", file=sys.stderr)
            try:
                import sounddevice as sd
                sd.play(audio, samplerate=sample_rate)
                sd.wait()
                print("[TTS-WORKER] Audio played.", file=sys.stderr)
            except Exception as play_err:
                print(f"[TTS-WORKER-ERROR] Playback failed: {play_err}", file=sys.stderr)

        print("[TTS-WORKER] Synthesis complete", file=sys.stderr)

    except Exception as e:
        print(f"[TTS-WORKER-ERROR] Exception during synthesis: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc(file=sys.stderr)

        # Очищаем CUDA кэш если возможно
        try:
            if _torch is not None and _torch.cuda.is_available():
                _torch.cuda.empty_cache()
        except Exception:
            pass

        # Если Silero недоступен, на Windows можно использовать системный SAPI как запасной вариант
        # Только для случая прямого воспроизведения (без сохранения в файл), чтобы не озвучивать на старте при генерации кеша
        if os.name == "nt" and sapi_enabled and not output:
            try:
                import win32com.client as wincl
                speak = wincl.Dispatch("SAPI.SpVoice")
                speak.Speak(text)
                print("Audio generated (SAPI fallback)")
                return
            except Exception as sapi_err:
                print(f"[TTS-WORKER-ERROR] SAPI fallback failed: {sapi_err}", file=sys.stderr)
        raise


def _read_text_from_stdin() -> str:
    """Read text from stdin with robust Windows encoding fallbacks (UTF-8, CP1251, CP866)."""
    try:
        data = sys.stdin.buffer.read()
    except Exception:
        # Fallback if buffer not available
        return sys.stdin.read()
    for enc in ("utf-8", "cp65001", "utf-16le", "cp1251", "cp866"):
        try:
            s = data.decode(enc)
            if s:
                return s
        except Exception:
            continue
    # Last resort: ignore errors
    try:
        return data.decode("utf-8", errors="ignore")
    except Exception:
        return ""


def main() -> None:
    parser = argparse.ArgumentParser(description="Arvis Silero TTS worker (subprocess)")
    parser.add_argument("--voice", default="aidar")
    parser.add_argument("--sample-rate", type=int, default=48000)
    parser.add_argument("--device", default="cpu")
    parser.add_argument("--output", default=None, help="Optional path to save WAV instead of playing")
    parser.add_argument("--sapi-enabled", action="store_true", help="Allow SAPI fallback on Windows")
    parser.add_argument("--text", default=None, help="Optional text to synthesize (otherwise read from stdin)")

    args = parser.parse_args()

    try:
        text_to_speak = args.text if args.text is not None else _read_text_from_stdin()
        synth_and_play(
            text=text_to_speak,
            voice=args.voice,
            sample_rate=args.sample_rate,
            device=args.device,
            output=args.output,
            sapi_enabled=bool(args.sapi_enabled),
        )
    except Exception as e:
        print(f"[TTS-WORKER-ERROR] {e}", file=sys.stderr)
        sys.exit(2)


if __name__ == "__main__":
    main()

