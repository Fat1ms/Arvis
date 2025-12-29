"""
Text-to-Speech engine using Silero TTS
"""

import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

import numpy as np
import sounddevice as sd
import soundfile as sf

# Torch may fail to import on some Windows setups due to DLL issues (c10.dll)
# Make it optional to allow the app to start with subprocess TTS fallback
try:
    import torch as _torch  # type: ignore
    _TORCH_IMPORT_ERROR: Optional[BaseException] = None
except BaseException as _e:  # ImportError or OSError (DLL load failure)
    _torch = None  # type: ignore
    _TORCH_IMPORT_ERROR = _e
from PyQt6.QtCore import QThread, pyqtSignal

from config.config import Config
from utils.logger import ModuleLogger


class TTSEngine:
    """Silero TTS engine for speech synthesis"""

    def __init__(self, config: Config):
        self.config = config
        self.logger = ModuleLogger("TTSEngine")
        self.model = None
        self.sample_rate = config.get("tts.sample_rate", 48000)
        self.voice = config.get("tts.voice", "aidar")
        self.device = config.get("tts.device", "cpu")
        self.is_ready_flag = False
        self._subprocess_available = False
        self.is_speaking = False
        self.current_audio = None
        self.tts_mode = config.get("tts.mode", "realtime")
        self.tts_enabled = config.get("tts.enabled", True)

        # Buffer for streaming mode to avoid word cutoffs
        self.text_buffer = ""
        self.min_buffer_size = 20  # Minimum characters before speaking
        self.word_boundary_chars = [" ", ".", ",", "!", "?", ";", ":", "\n", "\t"]

        # Initialize TTS
        self.init_tts()

    def _map_voice(self, voice: str) -> str:
        """Normalize voice aliases to real Silero speaker ids."""
        if not voice:
            return "aidar"
        v = voice.lower().strip()
        if v in {"ru_v3", "ru-v3", "v3", "default"}:
            return "aidar"
        return v

    def init_tts(self):
        """Initialize Silero TTS model"""
        try:
            self.logger.info("Initializing Silero TTS...")

            # Сначала проверим subprocess worker
            worker_path = Path(__file__).parent / "tts_worker_subprocess.py"
            self._subprocess_available = worker_path.exists()

            # Попробуем прямую загрузку Silero
            try:
                # Временно очищаем sys.path от конфликтующих путей
                original_path = sys.path.copy()
                current_dir = os.getcwd()

                # Удаляем все пути, содержащие текущий проект
                filtered_paths = []
                for path in sys.path:
                    path_abs = os.path.abspath(path) if path else ""
                    current_abs = os.path.abspath(current_dir)

                    # Не включаем пути к нашему проекту
                    if not path or path_abs == current_abs or current_abs in path_abs or "Arvis" in path_abs:
                        continue
                    filtered_paths.append(path)

                # Временно заменяем sys.path
                sys.path = filtered_paths

                # Если torch недоступен, пропускаем прямую загрузку и используем subprocess
                if _torch is None:
                    raise RuntimeError(
                        f"PyTorch not available: {_TORCH_IMPORT_ERROR}. Using subprocess-only TTS."
                    )

                # Загружаем модель (в разных версиях silero возвращается либо модель, либо кортеж)
                loaded = _torch.hub.load(
                    repo_or_dir="snakers4/silero-models",
                    model="silero_tts",
                    language="ru",
                    speaker="v3_1_ru",
                    verbose=False,
                )
                model = loaded[0] if isinstance(loaded, (tuple, list)) else loaded

                # Восстанавливаем sys.path
                sys.path = original_path

                # Тип модели для стат. анализатора неизвестен, приводим к Any
                model_any: Any = model
                model_any.to(self.device)
                self.model = model_any
                self.is_ready_flag = True
                self.logger.info("Silero TTS initialized successfully")

            except Exception as model_error:
                # Восстанавливаем sys.path в любом случае
                sys.path = original_path
                self.logger.warning(f"Direct TTS model loading failed: {model_error}")

                # Fallback - используем только subprocess
                if self._subprocess_available:
                    self.logger.info("Using subprocess-only TTS mode")
                    self.is_ready_flag = False  # Прямая модель не загружена
                    self.model = None
                else:
                    raise Exception(f"Neither direct model nor subprocess available: {model_error}")

        except Exception as e:
            self.logger.error(f"Failed to initialize TTS: {e}")
            self.is_ready_flag = False
            self.model = None

    def is_ready(self) -> bool:
        """Check if TTS engine is ready"""
        # Готов если модель загружена ИЛИ доступен subprocess fallback
        return (self.is_ready_flag and self.model is not None) or self._subprocess_available

    def speak(self, text: str, voice: Optional[str] = None):
        """Convert text to speech and play it asynchronously"""
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
                self.logger.info(f"Starting TTS for: {text[:50]}...")

                # Если прямая модель не загружена, используем subprocess
                if self.model is None:
                    self.logger.info("Direct model not available, using subprocess")
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

    def speak_streaming(self, text_chunk: str, voice: Optional[str] = None):
        """Speak text chunk for streaming mode (realtime) with buffering to avoid word cutoffs"""
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

    def flush_buffer(self, voice: Optional[str] = None):
        """Flush remaining text in buffer (call at end of generation)"""
        if self.text_buffer.strip():
            self.speak(self.text_buffer.strip(), voice)
            self.text_buffer = ""

    def speak_sentence(self, sentence: str, voice: Optional[str] = None):
        """Speak complete sentence for sentence-by-sentence mode"""
        if not self.tts_enabled or self.tts_mode != "sentence_by_sentence":
            return

        # Ждем окончания предыдущего воспроизведения перед новым
        if self.is_speaking:
            self.stop()

        self.speak(sentence, voice)

    def speak_complete(self, full_text: str, voice: Optional[str] = None):
        """Speak complete text after generation is finished"""
        if not self.tts_enabled or self.tts_mode != "after_complete":
            return

        self.speak(full_text, voice)

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

    def get_mode(self) -> str:
        """Get current TTS mode"""
        return str(self.tts_mode or "realtime")

    def _play_audio_async(self, audio_data):
        """Воспроизведение аудио в отдельном потоке"""
        import threading

        def play():
            try:
                self.is_speaking = True
                self.current_audio = audio_data

                try:
                    sd.play(audio_data, samplerate=self.sample_rate)
                    sd.wait()  # Ждём в отдельном потоке, не блокируя UI
                except Exception as pe:
                    # Перейти на сабпроцесс при ошибке воспроизведения
                    self.logger.error(f"Audio playback failed, using subprocess fallback: {pe}")
                    try:
                        text = ""  # невозможно восстановить исходный текст; просто остановим
                        # ничего не делаем, так как аудио уже сгенерировано; можно было бы сохранить и проиграть иным способом
                    except Exception:
                        pass

                self.is_speaking = False
                self.current_audio = None

            except Exception as e:
                self.logger.error(f"Error playing audio: {e}")
                self.is_speaking = False

        thread = threading.Thread(target=play, daemon=True)
        thread.start()

    def play_audio(self, audio_data: np.ndarray):
        """Play audio data without blocking the UI"""
        try:
            self.is_speaking = True
            self.current_audio = audio_data

            # Play audio using sounddevice (non-blocking)
            sd.play(audio_data, samplerate=self.sample_rate)
            # Don't wait here - let it play asynchronously
            # Check status in a separate thread or timer

        except Exception as e:
            self.logger.error(f"Error playing audio: {e}")
            self.is_speaking = False

    def check_playback_status(self):
        """Check if audio playback is still active"""
        try:
            if self.is_speaking and not sd.get_stream().active:
                self.is_speaking = False
                self.current_audio = None
        except Exception:
            self.is_speaking = False

    def stop(self):
        """Stop current TTS playback"""
        try:
            if self.is_speaking:
                sd.stop()
                self.is_speaking = False
                self.current_audio = None
                self.logger.info("TTS playback stopped")
        except Exception as e:
            self.logger.error(f"Error stopping TTS: {e}")

    def pause(self):
        """Pause TTS playback"""
        # Note: sounddevice doesn't support pause/resume directly
        # We'll stop playback for now
        self.stop()

    def resume(self):
        """Resume TTS playback"""
        # Since we can't truly pause/resume with sounddevice,
        # this is handled at a higher level
        pass

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
                self.logger.info(f"Audio saved to: {filename}")
                return True
            else:
                self.logger.error("Failed to generate audio for file")
                return False

        except Exception as e:
            self.logger.error(f"Error saving TTS to file with direct model: {e}. Trying subprocess fallback...")
            # Попробуем через сабпроцесс как запасной вариант
            return self._speak_via_subprocess(text, voice, output_filename=filename)

    def preload_phrases(self, phrases: List[str], limit: int = 1) -> Dict[str, List[np.ndarray]]:
        """Pre-generate audio clips for short acknowledgement phrases and persist them."""
        results: Dict[str, List[np.ndarray]] = {}

        if not phrases:
            return results

        try:
            temp_value = self.config.get("paths.temp", "temp")
            base_temp = Path(str(temp_value or "temp"))
        except Exception:
            base_temp = Path("temp")

        cache_dir = base_temp / "wake_ack"
        cache_dir.mkdir(parents=True, exist_ok=True)

        manifest_path = cache_dir / "manifest.json"
        manifest: Dict[str, List[str]] = {}
        try:
            if manifest_path.exists():
                manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        except Exception as manifest_error:
            self.logger.debug(f"Failed to read wake ack manifest: {manifest_error}")
            manifest = {}

        for phrase in phrases:
            if not phrase:
                continue

            bucket: List[np.ndarray] = []
            slug = hashlib.sha1(phrase.encode("utf-8")).hexdigest()
            stored_files = manifest.get(phrase, [])

            # Ensure we have up to 'limit' cached files per phrase
            while len(stored_files) < max(1, limit):
                index = len(stored_files)
                filename = f"ack_{slug}_{index}.wav"
                target_path = cache_dir / filename

                success = self.save_to_file(phrase, str(target_path))
                if not success:
                    self.logger.error(f"Failed to pre-generate wake acknowledgement for '{phrase}'")
                    break

                stored_files.append(filename)
                manifest[phrase] = stored_files
                try:
                    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
                except Exception as write_error:
                    self.logger.debug(f"Failed to update wake ack manifest: {write_error}")
                    # Не критично — продолжаем работу

            for filename in stored_files[: max(1, limit)]:
                wav_path = cache_dir / filename
                if not wav_path.exists():
                    self.logger.debug(f"Wake acknowledgement file missing, regenerating: {wav_path}")
                    if self.save_to_file(phrase, str(wav_path)) is False:
                        continue
                try:
                    audio, rate = sf.read(str(wav_path), dtype="float32")
                    if rate != self.sample_rate:
                        self.logger.debug(
                            f"Wake acknowledgement sample rate mismatch ({rate} != {self.sample_rate}), resaving"
                        )
                        # Перезаписываем файл с правильной частотой
                        sf.write(str(wav_path), audio, self.sample_rate)
                        audio, _ = sf.read(str(wav_path), dtype="float32")
                    bucket.append(np.asarray(audio, dtype=np.float32))
                except Exception as read_error:
                    self.logger.error(f"Failed to load wake acknowledgement clip '{wav_path}': {read_error}")

            if bucket:
                results[phrase] = bucket

        if results:
            self.logger.info(
                "Wake acknowledgement cache prepared: "
                + ", ".join(f"'{text}' -> {len(clips)} clip(s)" for text, clips in results.items())
            )

        return results

    def _speak_via_subprocess(self, text: str, voice: Optional[str] = None, output_filename: Optional[str] = None):
        """Use a dedicated subprocess worker to synthesize speech, avoiding import conflicts."""
        try:
            worker_path = Path(__file__).parent / "tts_worker_subprocess.py"
            if not worker_path.exists():
                self.logger.error(f"Subprocess worker not found: {worker_path}")
                return False

            voice = str(voice or self.voice)

            # Ограничиваем длину текста для стабильности
            original_length = len(text)
            if len(text) > 500:
                text = text[:500] + "..."
                self.logger.info(f"Text truncated from {original_length} to {len(text)} chars")

            self.logger.info(f"Starting subprocess TTS: '{text[:30]}...' with voice '{voice}'")

            args = [
                sys.executable,
                str(worker_path),
                "--text",
                text,
                "--voice",
                voice,
                "--sample-rate",
                str(self.sample_rate),
                "--device",
                self.device,
            ]
            # Проброс флага разрешения SAPI (по умолчанию выключен)
            if bool(self.config.get("tts.sapi_enabled", False)):
                args += ["--sapi-enabled"]
            if output_filename:
                args += ["--output", output_filename]

            # Увеличиваем timeout и улучшаем обработку ошибок
            try:
                # Динамический таймаут: даём достаточно времени на инициализацию 
                # sounddevice и загрузку модели на Windows
                timeout_sec = None
                try:
                    timeout_cfg = self.config.get("tts.subprocess_timeout_sec", None)
                    if isinstance(timeout_cfg, (int, float, str)):
                        timeout_sec = int(float(timeout_cfg))
                except Exception:
                    timeout_sec = None

                if timeout_sec is None or timeout_sec <= 0:
                    # Используем 45 сек — достаточно для первой загрузки и инициализации
                    timeout_sec = 45

                self.logger.debug(f"Running subprocess: {' '.join(args[:3])}... (timeout={timeout_sec}s)")
                result = subprocess.run(
                    args,
                    capture_output=True,
                    text=True,
                    timeout=timeout_sec,
                    creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
                )

                if result.returncode == 0:
                    self.logger.info("TTS subprocess completed successfully")
                    if result.stdout and result.stdout.strip():
                        self.logger.info(f"TTS subprocess: {result.stdout.strip()}")
                    return True
                else:
                    error_msg = result.stderr.strip() if result.stderr else "Unknown subprocess error"
                    self.logger.error(f"TTS subprocess failed (code {result.returncode}): {error_msg}")
                    return False

            except subprocess.TimeoutExpired:
                self.logger.error(f"TTS subprocess timed out after {timeout_sec}s")
                return False

        except Exception as e:
            self.logger.error(f"Failed to run TTS subprocess: {e}")
            return False

    def play_audio_array(self, audio: np.ndarray) -> bool:
        """Play an already synthesized audio buffer asynchronously."""
        if audio is None:
            return False

        try:
            self._play_audio_async(np.asarray(audio, dtype=np.float32))
            return True
        except Exception as playback_error:
            self.logger.error(f"Failed to play cached acknowledgement audio: {playback_error}")
            return False

    def get_available_voices(self) -> list:
        """Get list of available voices"""
        # Silero Russian voices
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

    def set_sample_rate(self, sample_rate: int):
        """Set sample rate"""
        if sample_rate in [8000, 24000, 48000]:
            self.sample_rate = sample_rate
            self.config.set("tts.sample_rate", sample_rate)
            self.logger.info(f"Sample rate set to: {sample_rate}")
            return True
        else:
            self.logger.error(f"Unsupported sample rate: {sample_rate}")
            return False

    def test_speech(self, text: str = "Привет! Это тест синтеза речи."):
        """Test TTS with sample text"""
        self.logger.info("Testing TTS...")
        self.speak(text)

    def get_status(self) -> dict:
        """Get TTS engine status"""
        return {
            "ready": self.is_ready(),
            "speaking": self.is_speaking,
            "voice": self.voice,
            "sample_rate": self.sample_rate,
            "device": self.device,
            "available_voices": self.get_available_voices(),
        }


class AsyncTTSEngine(QThread):
    """Asynchronous TTS engine for non-blocking operation"""

    speech_started = pyqtSignal()
    speech_finished = pyqtSignal()
    speech_error = pyqtSignal(str)

    def __init__(self, tts_engine: TTSEngine):
        super().__init__()
        self.tts_engine = tts_engine
        self.text_queue = []
        self.is_running = False

    def speak_async(self, text: str):
        """Add text to speech queue"""
        self.text_queue.append(text)
        if not self.is_running:
            self.start()

    def run(self):
        """Process speech queue"""
        self.is_running = True

        while self.text_queue:
            text = self.text_queue.pop(0)

            try:
                self.speech_started.emit()
                self.tts_engine.speak(text)
                self.speech_finished.emit()

            except Exception as e:
                self.speech_error.emit(str(e))

        self.is_running = False
