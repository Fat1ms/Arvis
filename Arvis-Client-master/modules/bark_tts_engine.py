"""
Bark TTS Engine - subprocess-based to avoid DLL issues in main process
"""

import sys
import os
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional

# Setup path for imports
project_root = Path(__file__).parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from config.config import Config
from modules.tts_base import TTSEngineBase, HealthCheckResult
from utils.logger import ModuleLogger


class BarkTTSEngine(TTSEngineBase):
    """Bark TTS engine wrapper that delegates synthesis to a subprocess worker.

    This design isolates PyTorch/Bark DLL dependencies from the main GUI process
    and prevents c10.dll errors from crashing or disabling the client.
    """

    def __init__(self, config: Config, logger: Optional[ModuleLogger] = None):
        super().__init__(config, logger or ModuleLogger("BarkTTSEngine"))

        # Settings
        self.voice = str(self.config.get("tts.bark.voice", "v2/multilingual_00") or "v2/multilingual_00")
        # Robust int parsing to avoid type checker issues if config returns dict/unknown
        _sr = self.config.get("tts.sample_rate", 24000)
        try:
            self.sample_rate = int(float(_sr))  # type: ignore[arg-type]
        except Exception:
            self.sample_rate = 24000
        self.device = str(self.config.get("tts.bark.device", "cpu") or "cpu")

        # Runtime
        self._worker_path = Path(__file__).parent / "bark_worker_subprocess.py"
        self.is_speaking = False
        self.text_buffer = ""
        self.min_buffer_size = 20
        self.word_boundary_chars = [" ", ".", ",", "!", "?", ";", ":", "\n", "\t"]
        self._disabled_reason: Optional[str] = None
        self.tts_enabled: bool = bool(self.config.get("tts.enabled", True))

        # Ready if worker exists (actual import checks happen inside worker)
        self.is_ready_flag = self._worker_path.exists()

    def _init_bark(self):
        """Deprecated: kept for backward compatibility (no-op)."""
        return

    # ===== Subprocess-based synthesis =====
    def _run_worker(self, text: str, output_path: Optional[str] = None) -> bool:
        try:
            if not self._worker_path.exists():
                self._disabled_reason = "Bark worker script not found"
                self.logger.error(str(self._disabled_reason))
                return False

            args = [
                sys.executable,
                str(self._worker_path),
                "--voice", str(self.voice),
                "--sample-rate", str(int(self.sample_rate)),
                "--device", str(self.device),
            ]

            if output_path:
                args += ["--output", str(output_path)]

            # To minimize start-up cost, pass text via stdin unless it is explicitly provided
            from subprocess import run, CREATE_NO_WINDOW

            timeout_sec = 60
            try:
                t_cfg = self.config.get("tts.subprocess_timeout_sec", None)
                if isinstance(t_cfg, (int, float, str)):
                    timeout_sec = int(float(t_cfg))
            except Exception:
                pass

            env = os.environ.copy()
            auto_install = bool(self.config.get("tts.bark.auto_install", True))
            env["ARVIS_BARK_AUTOINSTALL"] = "1" if auto_install else "0"

            result = run(
                args,
                input=text,
                capture_output=True,
                text=True,
                timeout=timeout_sec,
                creationflags=CREATE_NO_WINDOW if os.name == "nt" else 0,
                env=env,
            )

            if result.returncode == 0:
                if result.stdout:
                    self.logger.debug(result.stdout.strip())
                # If output_path provided, playback is handled by caller; otherwise worker plays audio itself
                return True
            else:
                err = (result.stderr or "").strip()
                self.logger.error(f"Bark worker failed (code {result.returncode}): {err[:500]}")
                if "c10.dll" in err.lower():
                    self._disabled_reason = "Torch DLL load failure (c10.dll)"
                elif "No module named 'bark'" in err or "ModuleNotFoundError: No module named 'bark'" in err:
                    self._disabled_reason = "Bark library not installed"
                return False

        except Exception as e:
            self.logger.error(f"Bark worker invocation error: {e}")
            return False

    # Kept for backward compatibility with old async loader (no-op)
    def _on_model_loaded(self, task_id, result):
        return

    def _on_model_load_error(self, task_id, error):
        return

    def save_to_file(self, text: str, output_path: str) -> bool:
        """Save TTS output to file"""
        return self._run_worker(text, output_path=output_path)

    def speak(self, text: str, voice: Optional[str] = None):
        """Convert text to speech and play it asynchronously
        
        Args:
            text: Text to synthesize
            voice: Optional voice name
        """
        if not text or not text.strip():
            return
        if not self.tts_enabled:
            self.logger.debug("Bark TTS disabled, skipping speak()")
            return False
        if self._disabled_reason:
            self.logger.warning(f"Bark TTS disabled: {self._disabled_reason}. Skipping speak().")
            return False

        # Run synthesis in async worker (to not block GUI)
        from utils.async_manager import task_manager

        def task():
            ok = self._run_worker(text)
            if ok:
                try:
                    self.playback_finished.emit()
                except Exception:
                    pass
            else:
                # Optional fallback to SAPI if explicitly enabled
                sapi_ok = self._speak_via_sapi(text)
                try:
                    # В любом исходе эмитим завершение чтобы Live-цепочка не зависала
                    self.playback_finished.emit()
                except Exception:
                    pass
            return ok

        import time
        task_id = f"bark_speak_{int(time.time()*1000)}"
        task_manager.run_async(task_id, task)

    def speak_streaming(self, text_chunk: str, voice: Optional[str] = None):
        """Speak text chunk for streaming mode with buffering
        
        Args:
            text_chunk: Text chunk to add to buffer
            voice: Optional voice name
        """
        if not text_chunk:
            return
        
        # Add chunk to buffer
        self.text_buffer += text_chunk
        
        # Check if we have enough text
        if len(self.text_buffer) >= self.min_buffer_size:
            # Find the last word boundary
            speak_text = ""
            remaining_buffer = self.text_buffer
            
            # Look for the last word boundary to avoid cutting words
            for i in range(len(self.text_buffer) - 1, -1, -1):
                if self.text_buffer[i] in self.word_boundary_chars:
                    speak_text = self.text_buffer[: i + 1].strip()
                    remaining_buffer = self.text_buffer[i + 1 :]
                    break
            
            # If no boundary found but buffer is too large, speak anyway
            if not speak_text and len(self.text_buffer) > self.min_buffer_size * 2:
                speak_text = self.text_buffer
                remaining_buffer = ""
            
            # Speak the text if we have something to say
            if speak_text:
                self.speak(speak_text, voice)
                self.text_buffer = remaining_buffer

    def stop(self):
        """Stop current TTS playback (best-effort)."""
        try:
            # We can't directly stop subprocess playback; rely on short phrases.
            self.is_speaking = False
            try:
                self.playback_finished.emit()
            except Exception:
                pass
        except Exception as e:
            self.logger.error(f"Error stopping Bark TTS: {e}")

    def flush_buffer(self, voice: Optional[str] = None):
        """Flush remaining text in buffer
        
        Args:
            voice: Optional voice name
        """
        if self.text_buffer.strip():
            self.speak(self.text_buffer.strip(), voice)
            self.text_buffer = ""

    def health_check(self) -> HealthCheckResult:
        """Check if the Bark worker is available (non-intrusive)."""
        try:
            if not self._worker_path.exists():
                return HealthCheckResult(False, "Bark worker missing", {"worker": str(self._worker_path)})
            if self._disabled_reason:
                return HealthCheckResult(False, f"Bark disabled: {self._disabled_reason}", {"error": self._disabled_reason})
            return HealthCheckResult(True, "Bark worker available", {"voice": self.voice, "device": self.device})
        except Exception as e:
            return HealthCheckResult(False, f"Health check error: {e}")

    # Subprocess synthesis only; keep API surface compatible
    def _synthesize(self, text: str, voice: Optional[str] = None):  # legacy signature
        self.logger.debug("Bark _synthesize called (no-op, using subprocess)")
        return None

    # Playback now handled within worker when no output file is specified
    def _play_audio_async(self, audio_data):  # legacy compat
        return

    def is_ready(self) -> bool:
        return bool(self.is_ready_flag and self._worker_path.exists() and not self._disabled_reason)

    def get_available_voices(self) -> List[str]:
        """Get list of available voices
        
        Returns:
            List of available voice names (English speakers + multilingual)
        """
        # Bark English speakers (native)
        english_speakers = [
            "v2/en_speaker_0",
            "v2/en_speaker_1", 
            "v2/en_speaker_2",
            "v2/en_speaker_3",
            "v2/en_speaker_4",
            "v2/en_speaker_5",
            "v2/en_speaker_6",
            "v2/en_speaker_7",
            "v2/en_speaker_8",
            "v2/en_speaker_9",
        ]
        
        # Multilingual voices (experimental support for RU/UK/EN)
        # These work for Russian and Ukrainian text, though Bark is primarily English
        multilingual_speakers = [
            "v2/multilingual_00",
            "v2/multilingual_01",
        ]
        
        return english_speakers + multilingual_speakers

    def set_voice(self, voice: str) -> bool:
        """Set active voice
        
        Args:
            voice: Voice name
            
        Returns:
            True if voice was set, False otherwise
        """
        available_voices = self.get_available_voices()
        if voice in available_voices:
            self.voice = voice
            self.config.set("tts.bark.voice", voice)
            self.logger.info(f"Voice set to: {voice}")
            return True
        else:
            self.logger.warning(f"Voice {voice} not available")
            return False

    def set_mode(self, mode: str):
        """Set TTS mode (for compatibility with SileroTTSEngine)
        
        Args:
            mode: Mode name (realtime, sentence_by_sentence, after_complete)
        """
        # Bark doesn't have different modes, but accept and log for compatibility
        self.logger.debug(f"TTS mode requested: {mode} (Bark doesn't have modes)")

    def set_enabled(self, enabled: bool):
        """Enable or disable TTS (for compatibility with SileroTTSEngine)
        
        Args:
            enabled: True to enable, False to disable
        """
        self.tts_enabled = bool(enabled)
        self.logger.debug(f"TTS enable requested: {enabled}")

    def _speak_via_sapi(self, text: str):
        """Fallback to SAPI on Windows when Bark synthesis not available"""
        try:
            # Respect global config flag
            try:
                if not bool(self.config.get("tts.sapi_enabled", False)):
                    self.logger.debug("SAPI fallback disabled by config; skipping")
                    return False
            except Exception:
                self.logger.debug("SAPI fallback disabled by default; skipping")
                return False

            self.logger.info(f"Bark failed, using SAPI fallback: '{text[:30]}...'")

            # На Windows используем встроенный SAPI для озвучки
            if os.name == "nt":
                try:
                    import pyttsx3
                    engine = pyttsx3.init()
                    engine.setProperty('rate', 150)  # Speed
                    engine.say(text)
                    engine.runAndWait()
                    self.logger.info("Audio played via SAPI")
                    return True
                except Exception as pyttsx_err:
                    self.logger.warning(f"pyttsx3 not available: {pyttsx_err}, trying win32com")

            # Fallback to win32com SAPI
            try:
                import win32com.client as wincl
                speak = wincl.Dispatch("SAPI.SpVoice")
                speak.Speak(text)
                self.logger.info("Audio played via win32com SAPI")
                return True
            except Exception as win32_err:
                self.logger.error(f"win32com SAPI also failed: {win32_err}")
                return False

        except Exception as e:
            self.logger.error(f"SAPI fallback error: {e}")
            return False

    def get_status(self) -> dict:
        """Get TTS engine status
        
        Returns:
            Status dictionary
        """
        return {
            "engine": "bark",
            "ready": self.is_ready(),
            "speaking": self.is_speaking,
            "device": self.device,
            "voice": self.voice,
            "enabled": self.tts_enabled,
            "available_voices": self.get_available_voices(),
        }
