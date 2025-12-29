"""
Silero TTS Engine - refactored to inherit from TTSEngineBase
Силеро TTS Движок - рефакторирован для наследования от TTSEngineBase
"""

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

import numpy as np
import sounddevice as sd
import soundfile as sf

# Make torch optional to avoid DLL crashes on Windows at import time
try:
    import torch as _torch  # type: ignore
    _TORCH_IMPORT_ERROR = None
except BaseException as _e:  # ImportError or OSError (DLL load failure)
    _torch = None  # type: ignore
    _TORCH_IMPORT_ERROR = _e

# Setup path for imports
project_root = Path(__file__).parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from config.config import Config
from modules.tts_base import TTSEngineBase, TTSStatus, HealthCheckResult
from utils.logger import ModuleLogger


class SileroTTSEngine(TTSEngineBase):
    """Silero TTS engine for speech synthesis"""

    def __init__(self, config: Config, logger: Optional[ModuleLogger] = None):
        """Initialize Silero TTS engine
        
        Args:
            config: Application configuration
            logger: Optional logger instance
        """
        super().__init__(config, logger or ModuleLogger("SileroTTSEngine"))
        self.model = None
        self.sample_rate = config.get("tts.sample_rate", 48000)
        self.voice = config.get("tts.voice", "aidar")
        self.device = config.get("tts.device", "cpu")
        self.is_ready_flag = False
        self._subprocess_available = False
        self.is_speaking = False
        self.current_audio = None
        self.tts_mode = config.get("tts.mode", "after_complete")  # Default: озвучка после генерации
        self.tts_enabled = config.get("tts.enabled", True)

        # Buffer for streaming mode to avoid word cutoffs
        self.text_buffer = ""
        self.min_buffer_size = 20  # Minimum characters before speaking
        self.word_boundary_chars = [" ", ".", ",", "!", "?", ";", ":", "\n", "\t"]

        # Lazy loading flag - model will be loaded on first use
        self._model_initialized = False
        self._model_loading = False
        # Detect subprocess worker availability early so health_check can pass
        try:
            worker_path = Path(__file__).parent / "tts_worker_subprocess.py"
            self._subprocess_available = worker_path.exists()
        except Exception:
            # Keep default False on error
            pass

    def _load_model_lazy(self):
        """Lazy load Silero model on first use (to avoid blocking in __init__)"""
        if self._model_initialized or self._model_loading:
            return
        
        self._model_loading = True
        try:
            self.logger.info("Loading Silero TTS model (lazy init)...")

            # Сначала проверим subprocess worker
            worker_path = Path(__file__).parent / "tts_worker_subprocess.py"
            self._subprocess_available = worker_path.exists()

            # Попробуем прямую загрузку Silero
            if _torch is None:
                raise RuntimeError(f"PyTorch not available: {_TORCH_IMPORT_ERROR}")
            
            try:
                self.logger.info("torch.hub.load() starting...")
                
                # Add cache dir to sys.path to fix import errors
                cache_dir = Path.home() / ".cache" / "torch" / "hub" / "snakers4_silero-models_master"
                if cache_dir.exists() and str(cache_dir) not in sys.path:
                    sys.path.insert(0, str(cache_dir))
                
                # Load model with trust_repo to avoid prompts
                loaded = _torch.hub.load(
                    repo_or_dir="snakers4/silero-models",
                    model="silero_tts",
                    language="ru",
                    speaker="v3_1_ru",
                    verbose=False,
                    trust_repo=True,
                )
                
                # Handle both single model and tuple returns
                model = loaded[0] if isinstance(loaded, (tuple, list)) else loaded
                
                # Move to device and store
                model_any: Any = model
                model_any.to(self.device)
                self.model = model_any
                self.is_ready_flag = True
                self._model_initialized = True
                self.logger.info("Silero TTS model loaded successfully")

            except Exception as model_error:
                self.logger.warning(f"Silero model loading failed: {model_error}")
                # Mark as initialized but model not loaded - will use fallback
                self._model_initialized = True
                self.is_ready_flag = False
                self.model = None

        except Exception as e:
            self.logger.error(f"Failed to initialize TTS: {e}")
            self._model_initialized = True
            self.is_ready_flag = False
            self.model = None
        finally:
            self._model_loading = False

    def _map_voice(self, voice: str) -> str:
        """Normalize voice aliases to real Silero speaker ids"""
        if not voice:
            return "aidar"
        v = voice.lower().strip()
        if v in {"ru_v3", "ru-v3", "v3", "default"}:
            return "aidar"
        return v

    def speak(self, text: str, voice: Optional[str] = None):
        """Convert text to speech and play it asynchronously
        
        Args:
            text: Text to synthesize
            voice: Optional voice name
        """
        # Проверяем, включена ли TTS в настройках
        if not self.tts_enabled:
            self.logger.debug("TTS disabled in settings, skipping speech")
            return

        if self.is_speaking:
            self.logger.warning("Already speaking, stopping current playback")
            self.stop()

        from utils.async_manager import task_manager

        def tts_task():
            try:
                # Lazy load model on first use
                if not self._model_initialized:
                    self.logger.info("First TTS use - loading model lazily...")
                    self._load_model_lazy()

                self.logger.info(f"Starting TTS for: {text[:50]}...")

                # Если прямая модель не загружена, используем subprocess
                if self.model is None:
                    self.logger.info("Direct model not available, using fallback")
                    return self._speak_via_subprocess(text, voice)

                # Если модель загружена, используем её
                self.logger.info(f"Using direct model for speech: {text[:50]}...")
                speaker_val: Union[str, Any] = voice if voice is not None else self.voice
                speaker = str(speaker_val) if not isinstance(speaker_val, str) else speaker_val
                speaker = self._map_voice(speaker)

                model_any: Any = self.model
                audio = model_any.apply_tts(text=text, speaker=speaker, sample_rate=self.sample_rate)

                if audio is not None:
                    if _torch is not None and hasattr(_torch, "is_tensor") and _torch.is_tensor(audio):
                        audio = audio.cpu().numpy()

                    # Запускаем воспроизведение в отдельном потоке
                    self._play_audio_async(audio)
                    return True
                else:
                    self.logger.error("Failed to generate audio")
                    return False

            except Exception as e:
                self.logger.error(f"Error in TTS: {e}")
                return self._speak_via_subprocess(text, voice)

        # Запускаем TTS асинхронно с уникальным именем
        import time
        unique_task_name = f"tts_speak_{int(time.time() * 1000)}"
        task_manager.run_async(unique_task_name, tts_task)

    def save_to_file(self, text: str, output_path: str) -> bool:
        """Save TTS output to file"""
        try:
            if not self._model_initialized:
                self._load_model_lazy()
            
            if self.model is None:
                self.logger.error("Cannot save to file: Direct model not loaded")
                return False

            speaker_val: Union[str, Any] = self.voice
            speaker = str(speaker_val) if not isinstance(speaker_val, str) else speaker_val
            speaker = self._map_voice(speaker)
            
            model_any: Any = self.model
            
            # Silero model usually has save_wav method
            if hasattr(model_any, 'save_wav'):
                 model_any.save_wav(text=text, speaker=speaker, sample_rate=self.sample_rate, audio_path=output_path)
                 return True
            
            # Fallback: get audio and save manually
            audio = model_any.apply_tts(text=text, speaker=speaker, sample_rate=self.sample_rate)
            if audio is not None:
                if _torch is not None and hasattr(_torch, "is_tensor") and _torch.is_tensor(audio):
                    audio = audio.cpu().numpy()
                
                import soundfile as sf
                sf.write(output_path, audio, self.sample_rate)
                return True
                
            return False
        except Exception as e:
            self.logger.error(f"Failed to save TTS to file: {e}")
            return False

    def speak_streaming(self, text_chunk: str, voice: Optional[str] = None):
        """Speak text chunk for streaming mode (realtime) with buffering
        
        Args:
            text_chunk: Text chunk to add to buffer
            voice: Optional voice name
        """
        if not self.tts_enabled or self.tts_mode != "realtime":
            return

        # Add chunk to buffer
        self.text_buffer += text_chunk

        # Check if we have enough text and can find a good breaking point
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
        """Stop current TTS playback"""
        try:
            if self.is_speaking:
                sd.stop()
                self.is_speaking = False
                self.current_audio = None
                try:
                    self.playback_finished.emit()
                except Exception:
                    pass
                self.logger.info("TTS playback stopped")
        except Exception as e:
            self.logger.error(f"Error stopping TTS: {e}")

    def flush_buffer(self, voice: Optional[str] = None):
        """Flush remaining text in buffer (call at end of generation)
        
        Args:
            voice: Optional voice name
        """
        if self.text_buffer.strip():
            self.speak(self.text_buffer.strip(), voice)
            self.text_buffer = ""

    def health_check(self) -> HealthCheckResult:
        """Check TTS engine health
        
        Returns:
            HealthCheckResult with health status
        """
        try:
            # Check basic readiness
            if not self.is_ready():
                return HealthCheckResult(
                    healthy=False,
                    message="TTS engine not ready",
                    details={"model_loaded": self.model is not None, "subprocess_available": self._subprocess_available}
                )

            # Check model if available
            if self.model is not None:
                try:
                    # Try a quick TTS generation
                    model_any: Any = self.model
                    audio = model_any.apply_tts(
                        text="тест",
                        speaker=self._map_voice(str(self.voice or "")),
                        sample_rate=self.sample_rate
                    )
                    if audio is None:
                        return HealthCheckResult(
                            healthy=False,
                            message="TTS audio generation failed",
                            details={"test_audio": None}
                        )
                except Exception as e:
                    return HealthCheckResult(
                        healthy=False,
                        message=f"TTS health check failed: {str(e)[:100]}",
                        details={"error": str(e)[:100]}
                    )

            return HealthCheckResult(
                healthy=True,
                message="TTS engine healthy",
                details={"voice": self.voice, "sample_rate": self.sample_rate, "device": self.device}
            )

        except Exception as e:
            return HealthCheckResult(
                healthy=False,
                message=f"Health check error: {str(e)[:100]}",
                details={"error": str(e)[:100]}
            )

    def is_ready(self) -> bool:
        """Check if TTS engine is ready"""
        # Готов если модель загружена ИЛИ доступен subprocess fallback
        return (self.is_ready_flag and self.model is not None) or self._subprocess_available

    def _play_audio_async(self, audio_data):
        """Play audio asynchronously"""
        import threading

        def play():
            try:
                self.is_speaking = True
                self.current_audio = audio_data

                try:
                    sd.play(audio_data, samplerate=self.sample_rate)
                    sd.wait()  # Wait in separate thread, don't block UI
                except Exception as pe:
                    self.logger.error(f"Audio playback failed: {pe}")

                self.is_speaking = False
                self.current_audio = None
                try:
                    self.playback_finished.emit()
                except Exception:
                    pass

            except Exception as e:
                self.logger.error(f"Error playing audio: {e}")
                self.is_speaking = False
                try:
                    self.playback_finished.emit()
                except Exception:
                    pass

        thread = threading.Thread(target=play, daemon=True)
        thread.start()

    def _speak_via_subprocess(self, text: str, voice: Optional[str] = None, output_filename: Optional[str] = None):
        """Use subprocess worker for fallback synthesis, respecting SAPI flag"""
        try:
            worker_path = Path(__file__).parent / "tts_worker_subprocess.py"
            if not worker_path.exists():
                self.logger.error(f"Subprocess worker not found: {worker_path}")
                return False

            voice_str = str(voice or self.voice)

            # Limit text length for stability
            original_length = len(text)
            if len(text) > 500:
                text = text[:500] + "..."
                self.logger.info(f"Text truncated from {original_length} to {len(text)} chars")

            args = [
                sys.executable,
                str(worker_path),
                "--voice",
                voice_str,
                "--sample-rate",
                str(self.sample_rate),
                "--device",
                str(self.device),
            ]

            # Respect SAPI fallback flag
            if bool(self.config.get("tts.sapi_enabled", False)):
                args.append("--sapi-enabled")

            # Ensure we have an output file to then play
            temp_file_used = False
            if not output_filename:
                import time
                tmp_dir = Path(tempfile.gettempdir())
                output_filename = str(tmp_dir / f"arvis_silero_{int(time.time()*1000)}.wav")
                temp_file_used = True
            args += ["--output", str(output_filename)]

            self.logger.debug(f"Running TTS worker (fallback): {' '.join(args[:3])} ...")

            import subprocess

            timeout_sec: int = 45
            try:
                t_cfg = self.config.get("tts.subprocess_timeout_sec", None)
                if isinstance(t_cfg, (int, float, str)):
                    timeout_sec = int(float(t_cfg))
            except Exception:
                pass

            result = subprocess.run(
                args,
                input=text,
                capture_output=True,
                text=True,
                encoding="utf-8",
                timeout=timeout_sec,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
            )

            if result.returncode == 0:
                if result.stdout and result.stdout.strip():
                    self.logger.info(result.stdout.strip())
                # If we created a temp file, play it
                try:
                    if output_filename and Path(output_filename).exists():
                        data, sr = sf.read(output_filename, dtype='float32')
                        try:
                            sd.play(data, samplerate=sr)
                            sd.wait()
                            try:
                                self.playback_finished.emit()
                            except Exception:
                                pass
                        except Exception as pe:
                            self.logger.error(f"Audio playback failed: {pe}")
                finally:
                    # Optionally remove temp file
                    try:
                        if temp_file_used and output_filename and Path(output_filename).exists():
                            Path(output_filename).unlink()
                    except Exception:
                        pass
                return True
            else:
                err = result.stderr.strip() if result.stderr else "unknown error"
                self.logger.error(f"TTS worker failed (code {result.returncode}): {err}")
                try:
                    self.playback_finished.emit()
                except Exception:
                    pass
                return False

        except subprocess.TimeoutExpired:
            self.logger.error("TTS worker timed out")
            try:
                self.playback_finished.emit()
            except Exception:
                pass
            return False
        except Exception as e:
            self.logger.error(f"Failed in fallback synthesis: {e}")
            try:
                self.playback_finished.emit()
            except Exception:
                pass
            return False

    def save_to_file(self, text: str, filename: str, voice: Optional[str] = None) -> bool:
        """Save TTS audio to file"""
        # Если прямая модель не загружена, сразу используем сабпроцесс
        if self.model is None:
            self.logger.info("Direct model unavailable, using subprocess to save file")
            return self._speak_via_subprocess(text, voice, output_filename=filename)

        try:
            speaker = str(voice or self.voice)
            speaker = self._map_voice(speaker)

            # Generate audio
            model_any: Any = self.model
            audio = model_any.apply_tts(text=text, speaker=speaker, sample_rate=self.sample_rate)

            if audio is not None:
                # Convert to numpy array if needed
                if _torch is not None and hasattr(_torch, "is_tensor") and _torch.is_tensor(audio):
                    audio = audio.cpu().numpy()

                # Save to file
                sf.write(filename, audio, self.sample_rate)
                self.logger.info(f"✓ Audio saved to: {filename}")
                return True
            else:
                self.logger.error("Failed to generate audio for file")
                return False

        except Exception as e:
            self.logger.error(f"Error saving TTS to file: {e}. Trying subprocess fallback...")
            return self._speak_via_subprocess(text, voice, output_filename=filename)

    def get_available_voices(self) -> list:
        """Get list of available voices"""
        return [
            "aidar",  # Male
            "baya",  # Female
            "kseniya",  # Female
            "xenia",  # Female
            "eugene",  # Male
            "ru_v3",  # Default
        ]

    def set_voice(self, voice: str):
        """Set active voice"""
        available_voices = self.get_available_voices()
        if voice in available_voices:
            self.voice = voice
            self.config.set("tts.voice", voice)
            self.logger.info(f"Voice set to: {voice}")
            return True
        else:
            self.logger.error(f"Voice {voice} not available")
            return False

    def set_mode(self, mode: str):
        """Set TTS mode: realtime, sentence_by_sentence, after_complete"""
        if mode in ["realtime", "sentence_by_sentence", "after_complete"]:
            self.tts_mode = mode
            self.logger.info(f"TTS mode set to: {mode}")
        else:
            self.logger.warning(f"Unknown TTS mode: {mode}")

    def set_enabled(self, enabled: bool):
        """Enable or disable TTS"""
        self.tts_enabled = enabled
        if not enabled and self.is_speaking:
            self.stop()
        self.logger.info(f"TTS {'enabled' if enabled else 'disabled'}")
