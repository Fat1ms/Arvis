"""
Speech-to-Text engine using Vosk
"""

import json
import re
import threading
import time
from pathlib import Path
from typing import Optional

try:
    import pyaudio
except ImportError:
    pyaudio = None

import vosk
from PyQt6.QtCore import QObject, QThread, pyqtSignal

from config.config import Config
from utils.logger import ModuleLogger

# If pyaudio is not available, define fallback constants
if pyaudio is None:
    class PyAudioFallback:
        """Minimal fallback shim to avoid attribute errors when PyAudio is missing."""
        # Standard PCM format constant used by code
        paInt16 = 2

        class PyAudio:
            def __init__(self, *args, **kwargs):
                # Explicit error to be caught by initialization logic
                raise RuntimeError("PyAudio is not installed. Please install pyaudio to enable microphone input.")

    # Assign the class (module-like shim), not an instance, so attribute lookups work
    pyaudio = PyAudioFallback


class STTEngine(QObject):
    """Vosk-based Speech-to-Text engine"""

    # Signals
    wake_word_detected = pyqtSignal()
    speech_recognized = pyqtSignal(str)
    recording_started = pyqtSignal()
    recording_stopped = pyqtSignal()
    model_ready = pyqtSignal(str)

    def __init__(self, config: Config):
        super().__init__()
        self.config = config
        self.logger = ModuleLogger("STTEngine")

        # Last audio init/recording error (used by controllers to show a more accurate message)
        self.last_audio_error: Optional[str] = None

        # Configuration
        self.model_path = config.get("stt.model_path", "models/vosk-model-small-ru-0.22")
        self.wake_word = config.get("stt.wake_word", "арвис").lower()
        # Добавляем распространенные варианты произношения, которые может распознать Vosk
        self.wake_word_variants = [self.wake_word, "арвис", "арвіс", "arvis"]
        try:
            accept_jarvis = bool(config.get("stt.wake_accept_jarvis", False))
        except Exception:
            accept_jarvis = False
        if accept_jarvis:
            self.wake_word_variants.extend(["джарвис", "jarvis"])
        self.sample_rate = 16000
        self.chunk_size = 1024

        # Wake word detection tuning
        try:
            self.wake_use_grammar = bool(config.get("stt.wake_use_grammar", True))
        except Exception:
            self.wake_use_grammar = True
        try:
            val = config.get("stt.wake_fuzzy_distance", 1)
            self.wake_fuzzy_distance = int(val) if isinstance(val, (int, float, str)) else 1
        except Exception:
            self.wake_fuzzy_distance = 1

        # State
        self.is_recording = False
        self.is_listening_for_wake_word = False
        self.model = None
        self.recognizer = None
        self.audio_stream = None
        self.audio_interface = None

        # Threading
        self.recording_thread = None
        self.wake_word_thread = None

        # Initialize
        self.init_stt()

    def init_stt(self):
        """Initialize Vosk STT model"""
        try:
            self.logger.info("Initializing Vosk STT...")

            # Resolve model path with fallback to best available local model
            resolved_model_path = self._resolve_best_model_path(self.model_path)
            if resolved_model_path and resolved_model_path != self.model_path:
                try:
                    self.logger.info(f"STT model path resolved to: {resolved_model_path}")
                    self.model_path = resolved_model_path
                    # Persist if config supports set()
                    try:
                        self.config.set("stt.model_path", resolved_model_path)
                    except Exception:
                        pass
                except Exception:
                    pass

            # Check if model exists
            model_path = Path(self.model_path)
            if not model_path.exists():
                self.logger.error(f"Vosk model not found at: {model_path}")
                self.logger.info("Please download a Vosk model and update the path in settings")
                return

            # Load model
            self.model = vosk.Model(str(model_path))
            self.recognizer = vosk.KaldiRecognizer(self.model, self.sample_rate)

            # Defer PyAudio initialization to first use to avoid startup crashes
            self.audio_interface = None

            self.logger.info("Vosk STT initialized successfully (PyAudio will init on first use)")

            try:
                self.model_ready.emit(str(model_path))
            except Exception as emit_error:
                self.logger.debug(f"Failed to emit model_ready signal: {emit_error}")

        except Exception as e:
            self.logger.error(f"Failed to initialize STT: {e}")

    def is_ready(self) -> bool:
        """Check if STT engine is ready"""
        return self.model is not None and self.recognizer is not None

    def get_model(self) -> Optional[vosk.Model]:
        """Provide direct access to the underlying Vosk model (if loaded)."""
        return self.model

    def _ensure_audio_interface(self):
        """Lazily initialize PyAudio interface if not yet created."""
        if pyaudio is None or not hasattr(pyaudio, "PyAudio"):
            # Downgrade to warning to avoid alarming logs when mic is optional
            self.logger.warning("PyAudio is not installed. Microphone input disabled.")
            self.last_audio_error = "PyAudio is not installed"
            return False
            
        if self.audio_interface is None:
            try:
                # Initialize PyAudio with error handling for Windows
                self.audio_interface = pyaudio.PyAudio()
                self.logger.info("PyAudio interface initialized successfully")
                self.last_audio_error = None
            except Exception as e:
                self.logger.warning(f"Failed to initialize audio interface: {e}")
                self.last_audio_error = str(e)
                # Try to provide helpful information
                if "ALSA" in str(e):
                    self.logger.info("ALSA errors are usually harmless on non-Linux systems")
                elif "PortAudio" in str(e):
                    self.logger.warning("PortAudio not properly installed. Please check audio system.")
                return False
        return True

    def start_wake_word_detection(self) -> bool:
        """Start listening for wake word in background"""
        if not self.is_ready():
            self.logger.error("STT engine not ready")
            return False

        if self.is_listening_for_wake_word:
            self.logger.warning("Already listening for wake word")
            return False

        # Avoid device contention
        if self.is_recording:
            self.logger.warning("Wake word detection not started: recording is active")
            self.last_audio_error = "recording is active"
            return False

        # Fail-fast: do not mark wake listening active if audio is unavailable
        if not self._ensure_audio_interface():
            self.is_listening_for_wake_word = False
            self.logger.warning("Wake word detection not started: audio interface unavailable")
            return False

        self.is_listening_for_wake_word = True
        self.wake_word_thread = threading.Thread(target=self._wake_word_loop, daemon=True)
        self.wake_word_thread.start()
        self.logger.info("Started wake word detection")
        return True

    def stop_wake_word_detection(self):
        """Stop wake word detection"""
        self.is_listening_for_wake_word = False
        if self.wake_word_thread:
            self.wake_word_thread.join(timeout=1.0)
        self.logger.info("Stopped wake word detection")

    def _wake_word_loop(self):
        """Background loop for wake word detection"""
        stream = None
        try:
            # Audio interface is expected to be initialized by start_wake_word_detection().
            if self.audio_interface is None and not self._ensure_audio_interface():
                self.is_listening_for_wake_word = False
                return

            # Create audio stream for wake word detection (may fail briefly if device is still releasing)
            last_open_error = None
            for _attempt in range(3):
                try:
                    stream = self.audio_interface.open(
                        format=pyaudio.paInt16,
                        channels=1,
                        rate=self.sample_rate,
                        input=True,
                        frames_per_buffer=self.chunk_size,
                    )
                    last_open_error = None
                    break
                except Exception as e:
                    last_open_error = e
                    time.sleep(0.15)

            if stream is None:
                self.last_audio_error = str(last_open_error) if last_open_error else "Failed to open microphone stream"
                self.logger.warning(f"Wake word stream open failed: {self.last_audio_error}")
                return

            # Prefer limited grammar to improve wake word precision
            wake_recognizer = None
            if self.wake_use_grammar:
                try:
                    # Include [unk] so recognizer can still emit something for debugging
                    grammar_tokens = sorted(set([v for v in self.wake_word_variants if isinstance(v, str) and v.strip()] + ["[unk]"]))
                    grammar = json.dumps(grammar_tokens, ensure_ascii=False)
                    wake_recognizer = vosk.KaldiRecognizer(self.model, self.sample_rate, grammar)
                except Exception as e:
                    self.logger.debug(f"Failed to init wake recognizer with grammar: {e}")
                    wake_recognizer = None
            if wake_recognizer is None:
                wake_recognizer = vosk.KaldiRecognizer(self.model, self.sample_rate)

            while self.is_listening_for_wake_word:
                try:
                    data = stream.read(self.chunk_size, exception_on_overflow=False)

                    if wake_recognizer.AcceptWaveform(data):
                        result = json.loads(wake_recognizer.Result())
                        text = result.get("text", "").lower()

                        # Логируем все распознанные фразы для отладки
                        if text:
                            self.logger.debug(f"Wake word loop recognized: '{text}'")

                        if self._is_wake_match(text):
                            self.logger.info(f"Wake word detected in: '{text}'")
                            self.wake_word_detected.emit()
                    else:
                        # Partial results help detect short wake words faster (and improve debug visibility)
                        try:
                            partial_result = json.loads(wake_recognizer.PartialResult())
                            partial_text = str(partial_result.get("partial", "") or "").lower().strip()
                        except Exception:
                            partial_text = ""
                        if partial_text:
                            self.logger.debug(f"Wake word loop partial: '{partial_text}'")
                            if self._is_wake_match(partial_text):
                                self.logger.info(f"Wake word detected in: '{partial_text}'")
                                self.wake_word_detected.emit()

                except Exception as e:
                    if self.is_listening_for_wake_word:  # Only log if we're still supposed to be listening
                        self.logger.debug(f"Error in wake word detection: {e}")

        except Exception as e:
            self.logger.error(f"Error in wake word loop: {e}")
        finally:
            # Ensure we don't get stuck in "Already listening" state if stream init fails
            self.is_listening_for_wake_word = False
            try:
                if stream is not None:
                    stream.close()
            except Exception:
                pass

    @staticmethod
    def _normalize_wake_text(text: str) -> str:
        if not isinstance(text, str):
            return ""
        # keep letters/digits; collapse spaces
        cleaned = re.sub(r"[^0-9a-zа-яё]+", " ", text.lower(), flags=re.IGNORECASE)
        cleaned = re.sub(r"\s+", " ", cleaned).strip()
        return cleaned

    @staticmethod
    def _levenshtein(a: str, b: str, max_distance: int) -> int:
        """Compute Levenshtein distance with early exit if it exceeds max_distance."""
        if a == b:
            return 0
        if not a:
            return len(b)
        if not b:
            return len(a)
        if abs(len(a) - len(b)) > max_distance:
            return max_distance + 1

        prev = list(range(len(b) + 1))
        for i, ca in enumerate(a, start=1):
            cur = [i]
            row_min = cur[0]
            for j, cb in enumerate(b, start=1):
                ins = cur[j - 1] + 1
                dele = prev[j] + 1
                sub = prev[j - 1] + (0 if ca == cb else 1)
                v = ins if ins < dele else dele
                if sub < v:
                    v = sub
                cur.append(v)
                if v < row_min:
                    row_min = v
            if row_min > max_distance:
                return max_distance + 1
            prev = cur
        return prev[-1]

    def _is_wake_match(self, recognized_text: str) -> bool:
        """Return True if recognized text likely contains wake word."""
        text = self._normalize_wake_text(recognized_text)
        if not text:
            return False

        variants = [self._normalize_wake_text(v) for v in self.wake_word_variants]
        variants = [v for v in variants if v]

        # Exact substring match first
        for v in variants:
            if v in text:
                return True

        # Fuzzy: compare each token and also collapsed tokens to catch split results like "арвид с"
        max_d = max(0, int(self.wake_fuzzy_distance))
        if max_d <= 0:
            return False

        tokens = text.split()
        collapsed = "".join(tokens)
        candidates = list(tokens)
        if collapsed:
            candidates.append(collapsed)

        for cand in candidates:
            for v in variants:
                if len(cand) < 3 or len(v) < 3:
                    continue
                # Prefix gate: drastically reduces false positives on small models
                prefix_len = 3
                if cand[:prefix_len] != v[:prefix_len]:
                    continue
                if self._levenshtein(cand, v, max_d) <= max_d:
                    return True
        return False

    def _resolve_best_model_path(self, configured_path: str) -> str:
        """Pick the best available Vosk model path.

        Respects user's choice if the configured path exists.
        Only auto-selects model if no valid path is configured.
        """
        try:
            cfg = str(configured_path or "").strip()
        except Exception:
            cfg = ""

        try:
            cfg_exists = bool(cfg) and Path(cfg).expanduser().exists()
        except Exception:
            cfg_exists = False

        # If configured path exists, use it (respect user's choice)
        if cfg_exists:
            return cfg

        # Try common local candidates if configured path doesn't exist
        candidates = [
            "models/vosk-model-small-ru-0.22",  # Small model first (faster)
            "models/vosk-model-ru-0.42",
            "models/vosk-model-ru-0.22",
            "models/vosk-model-small-en-us-0.15",
            "models/vosk-model-en-us-0.22",
        ]
        for rel in candidates:
            try:
                p = Path(rel)
                if p.exists():
                    return str(p)
            except Exception:
                continue

        # Fallback to whatever was configured
        return cfg

    def start_recording(self) -> bool:
        """Start recording for speech recognition"""
        if not self.is_ready():
            self.logger.error("STT engine not ready")
            return False

        if self.is_recording:
            self.logger.warning("Already recording")
            return False

        # Fail-fast: do not enter recording state if audio is unavailable
        if not self._ensure_audio_interface():
            self.is_recording = False
            self.logger.warning("Recording not started: audio interface unavailable")
            return False

        self.is_recording = True
        self.recording_thread = threading.Thread(target=self._recording_loop, daemon=True)
        self.recording_thread.start()
        self.recording_started.emit()
        self.logger.info("Started recording")
        return True

    def stop_recording(self):
        """Stop recording"""
        if self.is_recording:
            self.is_recording = False
            if self.recording_thread:
                self.recording_thread.join(timeout=2.0)
            self.logger.info("Stopped recording")

    def _recording_loop(self):
        """Main recording loop"""
        stream = None
        try:
            # Audio interface is expected to be initialized by start_recording().
            if self.audio_interface is None and not self._ensure_audio_interface():
                self.is_recording = False
                try:
                    self.recording_stopped.emit()
                except Exception:
                    pass
                return
            # Create audio stream for recording
            stream = self.audio_interface.open(
                format=pyaudio.paInt16, channels=1, rate=self.sample_rate, input=True, frames_per_buffer=self.chunk_size
            )

            # Create new recognizer for this session
            session_recognizer = vosk.KaldiRecognizer(self.model, self.sample_rate)

            speech_detected = False
            silence_counter = 0
            total_silence_counter = 0  # Счетчик полной тишины с начала записи
            max_silence = 40  # ~2.5 seconds of silence after speech to stop (увеличено)
            max_total_silence = 160  # ~10 seconds of complete silence from start to stop (увеличено вдвое)

            while self.is_recording:
                try:
                    data = stream.read(self.chunk_size, exception_on_overflow=False)

                    if session_recognizer.AcceptWaveform(data):
                        result = json.loads(session_recognizer.Result())
                        text = result.get("text", "").strip()

                        if text:
                            speech_detected = True
                            silence_counter = 0
                            total_silence_counter = 0
                            self.logger.info(f"Recognized: {text}")
                            self.speech_recognized.emit(text)
                            break  # Stop after recognizing speech
                    else:
                        # Check for partial results to detect speech activity
                        partial_result = json.loads(session_recognizer.PartialResult())
                        partial_text = partial_result.get("partial", "").strip()

                        if partial_text:
                            speech_detected = True
                            silence_counter = 0
                            total_silence_counter = 0
                            self.logger.debug(f"Partial: {partial_text}")
                        else:
                            # Тишина
                            if speech_detected:
                                silence_counter += 1
                                if silence_counter > max_silence:
                                    # Too much silence after detecting speech
                                    self.logger.info("Stopping: silence after speech detected")
                                    break
                            else:
                                # Полная тишина с начала записи
                                total_silence_counter += 1
                                if total_silence_counter > max_total_silence:
                                    # Пользователь ничего не сказал за 5 секунд
                                    self.logger.info("Stopping: no speech detected within timeout")
                                    break

                except Exception as e:
                    if self.is_recording:  # Only log if we're still supposed to be recording
                        self.logger.debug(f"Error in recording loop: {e}")

            # Get final result
            try:
                final_result = json.loads(session_recognizer.FinalResult())
                final_text = final_result.get("text", "").strip()
                if final_text and not speech_detected:
                    self.logger.info(f"Final recognized: {final_text}")
                    self.speech_recognized.emit(final_text)
                elif not speech_detected and not final_text:
                    # Пользователь ничего не сказал
                    self.logger.info("Recording ended with no speech detected")
                    # Эмитируем пустую строку чтобы сигнализировать об отсутствии речи
                    self.speech_recognized.emit("")
            except Exception as e:
                self.logger.debug(f"Error getting final result: {e}")

        except Exception as e:
            self.logger.error(f"Error in recording loop: {e}")
        finally:
            # Always reset recording state if the thread exits early (e.g. missing PyAudio)
            if self.is_recording:
                self.is_recording = False
            try:
                if stream is not None:
                    stream.close()
            except Exception:
                pass
            try:
                self.recording_stopped.emit()
            except Exception:
                pass

    def recognize_audio_file(self, file_path: str) -> Optional[str]:
        """Recognize speech from audio file"""
        if not self.is_ready():
            self.logger.error("STT engine not ready")
            return None

        try:
            import wave

            # Open audio file
            wf = wave.open(file_path, "rb")

            # Check audio format
            if wf.getnchannels() != 1 or wf.getsampwidth() != 2 or wf.getframerate() != self.sample_rate:
                self.logger.error("Audio file must be mono, 16-bit, 16kHz")
                return None

            # Create recognizer
            file_recognizer = vosk.KaldiRecognizer(self.model, self.sample_rate)

            # Process audio
            text_parts = []
            while True:
                data = wf.readframes(self.chunk_size)
                if len(data) == 0:
                    break

                if file_recognizer.AcceptWaveform(data):
                    result = json.loads(file_recognizer.Result())
                    text = result.get("text", "").strip()
                    if text:
                        text_parts.append(text)

            # Get final result
            final_result = json.loads(file_recognizer.FinalResult())
            final_text = final_result.get("text", "").strip()
            if final_text:
                text_parts.append(final_text)

            wf.close()

            full_text = " ".join(text_parts).strip()
            self.logger.info(f"File recognition result: {full_text}")
            return full_text if full_text else None

        except Exception as e:
            self.logger.error(f"Error recognizing audio file: {e}")
            return None

    def set_wake_word(self, wake_word: str):
        """Set wake word"""
        self.wake_word = wake_word.lower()
        self.config.set("stt.wake_word", wake_word)
        self.logger.info(f"Wake word set to: {wake_word}")

    def get_audio_devices(self):
        """Get available audio input devices"""
        if not self.audio_interface:
            return []

        devices = []
        try:
            for i in range(self.audio_interface.get_device_count()):
                device_info = self.audio_interface.get_device_info_by_index(i)
                if device_info["maxInputChannels"] > 0:
                    devices.append(
                        {"index": i, "name": device_info["name"], "channels": device_info["maxInputChannels"]}
                    )
        except Exception as e:
            self.logger.error(f"Error getting audio devices: {e}")

        return devices

    def test_microphone(self) -> bool:
        """Test microphone input"""
        try:
            self.logger.info("Testing microphone...")

            # Record for 3 seconds
            stream = self.audio_interface.open(
                format=pyaudio.paInt16, channels=1, rate=self.sample_rate, input=True, frames_per_buffer=self.chunk_size
            )

            frames = []
            for i in range(0, int(self.sample_rate / self.chunk_size * 3)):
                data = stream.read(self.chunk_size)
                frames.append(data)

            stream.close()

            # Check if we got some audio data
            total_audio = b"".join(frames)
            if len(total_audio) > 0:
                self.logger.info("Microphone test successful")
                return True
            else:
                self.logger.error("No audio data received")
                return False

        except Exception as e:
            self.logger.error(f"Microphone test failed: {e}")
            return False

    def cleanup(self):
        """Cleanup STT resources"""
        try:
            self.stop_wake_word_detection()
            self.stop_recording()

            if self.audio_interface:
                self.audio_interface.terminate()

            self.logger.info("STT cleanup complete")

        except Exception as e:
            self.logger.error(f"Error during STT cleanup: {e}")

    def get_status(self) -> dict:
        """Get STT engine status"""
        return {
            "ready": self.is_ready(),
            "recording": self.is_recording,
            "listening_for_wake_word": self.is_listening_for_wake_word,
            "wake_word": self.wake_word,
            "model_path": self.model_path,
            "sample_rate": self.sample_rate,
        }
