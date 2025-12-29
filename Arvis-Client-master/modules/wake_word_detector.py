"""Wake word detection helpers built on Kaldi (Vosk)."""

import json
import threading
import time
from pathlib import Path
from typing import List, Optional, Tuple

try:
    import pyaudio
except ImportError:
    pyaudio = None

import vosk
from PyQt6.QtCore import QObject, pyqtSignal

from config.config import Config
from utils.logger import ModuleLogger

# If pyaudio is not available, define fallback constants
if pyaudio is None:
    class PyAudioFallback:
        paInt16 = 2  # Standard PCM format constant
    pyaudio = PyAudioFallback()


def _safe_float(value, default: float) -> float:
    try:
        if isinstance(value, (int, float, str)):
            return float(value)
    except Exception:
        pass
    return default


def _safe_int(value, default: int) -> int:
    try:
        if isinstance(value, (int, float, str)):
            return int(float(value))
    except Exception:
        pass
    return default


def _ensure_list(value) -> List[str]:
    if isinstance(value, list):
        return [str(v).strip() for v in value if str(v).strip()]
    if isinstance(value, tuple):
        return [str(v).strip() for v in list(value) if str(v).strip()]
    if isinstance(value, str):
        cleaned = [item.strip() for item in value.replace("|", ",").split(",") if item.strip()]
        return cleaned
    return []


class KaldiWakeWordDetector(QObject):
    """Kaldi-based wake word detector implemented with Vosk grammar recognition."""

    wake_word_detected = pyqtSignal()

    def __init__(self, config: Config, shared_model: Optional[vosk.Model] = None):
        super().__init__()
        self.config = config
        self.logger = ModuleLogger("WakeWordDetector")

        # Configuration
        self._base_wake_word = str(self.config.get("stt.wake_word", "Арвис"))
        self.model_path = str(self.config.get("stt.kaldi_model_path", self.config.get("stt.model_path", "")))
        self.sample_rate = _safe_int(self.config.get("stt.kaldi_sample_rate", 16000), 16000)
        self.chunk_size = max(512, _safe_int(self.config.get("stt.kaldi_chunk_size", 2048), 2048))
        self.cooldown_sec = max(0.1, _safe_float(self.config.get("stt.kaldi_cooldown", 1.0), 1.0))
        self.use_grammar = bool(self.config.get("stt.kaldi_use_grammar", True))
        self.debug_log = bool(self.config.get("stt.kaldi_debug_log", False))
        # Поддержка выбора микрофона из config.audio.input_device (индекс или имя)
        try:
            self.input_device_pref = self.config.get("audio.input_device", None)
        except Exception:
            self.input_device_pref = None
        variants = self.config.get("stt.kaldi_wake_words", [])
        self._wake_variants = self._build_variant_list(variants)
        # Максимальная дистанция Левенштейна для нестрогого совпадения
        self._fuzzy_max_distance = _safe_int(self.config.get("stt.kaldi_fuzzy_distance", 1), 1)

        # State
        self.model: Optional[vosk.Model] = None
        self.recognizer: Optional[vosk.KaldiRecognizer] = None
        self.audio_interface: Optional[pyaudio.PyAudio] = None
        self.audio_stream = None
        self.is_listening = False
        self._detection_thread: Optional[threading.Thread] = None
        self._last_trigger_ts = 0.0
        self._shared_model = shared_model
        self._owns_model = False

        self.init_detector()

    # ------------------------------------------------------------------
    # Initialization helpers
    # ------------------------------------------------------------------
    def _build_variant_list(self, variants) -> List[str]:
        parsed = _ensure_list(variants)
        base = self._normalize_phrase(self._base_wake_word)
        if base and base not in parsed:
            parsed.insert(0, base)
        return [v for v in parsed if v]

    def _grammar(self) -> str:
        if not self._wake_variants:
            return '["[unk]"]'
        grammar = list(dict.fromkeys(self._wake_variants + ["[unk]"]))
        return json.dumps(grammar, ensure_ascii=False)

    def init_detector(self) -> bool:
        try:
            self.cleanup()

            model_path = Path(self.model_path).expanduser()
            if self._shared_model is not None:
                self.model = self._shared_model
                self._owns_model = False
            else:
                if not model_path.exists():
                    self.logger.error(
                        "Kaldi wake word model not found. Set 'stt.kaldi_model_path' or install a Vosk/Kaldi model."
                    )
                    return False

                self.logger.info("Initializing Kaldi wake word detector...")
                self.model = vosk.Model(str(model_path))
                self._owns_model = True

            self._create_recognizer()
            if self.model is not None and self.recognizer is not None:
                self.logger.info("Kaldi wake word detector initialized successfully")
                return True

            self.logger.error("Kaldi wake word detector failed to initialize recognizer")
            return False

        except Exception as exc:
            self.logger.error(f"Failed to initialize Kaldi wake word detector: {exc}")
            self.cleanup()
            return False

    def _create_recognizer(self):
        if not self.model:
            return
        try:
            if self.use_grammar:
                grammar = self._grammar()
                if self.debug_log:
                    self.logger.debug(f"Kaldi grammar: {grammar}")
                self.recognizer = vosk.KaldiRecognizer(self.model, self.sample_rate, grammar)
            else:
                self.recognizer = vosk.KaldiRecognizer(self.model, self.sample_rate)
            self.recognizer.SetWords(True)
        except Exception as exc:
            self.logger.error(f"Failed to create Kaldi recognizer: {exc}")
            self.recognizer = None

    def _ensure_audio_interface(self) -> bool:
        if self.audio_interface:
            return True
        try:
            self.audio_interface = pyaudio.PyAudio()
            return True
        except Exception as exc:
            self.logger.error(f"Failed to initialize audio interface for Kaldi wake word: {exc}")
            return False

    def _resolve_input_device_index(self) -> Optional[int]:
        """Определить индекс входного устройства на основе предпочтения пользователя."""
        if not self.audio_interface:
            return None
        pref = self.input_device_pref
        if pref is None or pref == "" or str(pref).lower() == "default":
            return None
        try:
            device_count = self.audio_interface.get_device_count()
            # Если указан индекс
            if isinstance(pref, int) or (isinstance(pref, str) and pref.isdigit()):
                idx = int(pref)
                if 0 <= idx < device_count:
                    return idx
                return None
            # Иначе — по имени (частичное совпадение, без регистра)
            pref_low = str(pref).lower()
            for i in range(device_count):
                try:
                    info = self.audio_interface.get_device_info_by_index(i)
                    if int(info.get("maxInputChannels", 0)) > 0 and pref_low in str(info.get("name", "")).lower():
                        return i
                except Exception:
                    continue
        except Exception:
            pass
        return None

    # ------------------------------------------------------------------
    # Control methods
    # ------------------------------------------------------------------
    def is_ready(self) -> bool:
        return self.model is not None and self.recognizer is not None

    def start_detection(self) -> bool:
        if self.is_listening:
            self.logger.debug("Kaldi wake word detector already running")
            return True

        if not self.is_ready():
            if not self.init_detector():
                return False

        if not self._ensure_audio_interface() or not self.recognizer:
            return False

        if not self.audio_interface:
            self.logger.error("Audio interface unavailable for Kaldi wake word detector")
            return False

        try:
            input_index = self._resolve_input_device_index()
            if self.debug_log:
                self.logger.debug(
                    f"Opening audio stream for Kaldi: rate={self.sample_rate}, chunk={self.chunk_size}, device={input_index if input_index is not None else 'default'}"
                )
            self.audio_stream = self.audio_interface.open(
                rate=self.sample_rate,
                channels=1,
                format=pyaudio.paInt16,
                input=True,
                input_device_index=input_index,
                frames_per_buffer=self.chunk_size,
            )
            self.is_listening = True
            self._last_trigger_ts = 0.0
            self._detection_thread = threading.Thread(target=self._detection_loop, daemon=True)
            self._detection_thread.start()
            self.logger.info("Kaldi wake word detection started")
            return True
        except Exception as exc:
            self.logger.error(f"Error starting Kaldi wake word detection: {exc}")
            # Попробуем альтернативные частоты, если не удалось запустить на заданной
            for alt_rate in (44100, 48000):
                try:
                    if self.debug_log:
                        self.logger.debug(f"Retrying audio stream with rate={alt_rate}")
                    self.audio_stream = self.audio_interface.open(
                        rate=alt_rate,
                        channels=1,
                        format=pyaudio.paInt16,
                        input=True,
                        input_device_index=self._resolve_input_device_index(),
                        frames_per_buffer=self.chunk_size,
                    )
                    # Пересоздаём распознаватель с новой частотой
                    if self.model:
                        if self.use_grammar:
                            self.recognizer = vosk.KaldiRecognizer(self.model, alt_rate, self._grammar())
                        else:
                            self.recognizer = vosk.KaldiRecognizer(self.model, alt_rate)
                        self.recognizer.SetWords(True)
                    self.sample_rate = alt_rate
                    self.is_listening = True
                    self._last_trigger_ts = 0.0
                    self._detection_thread = threading.Thread(target=self._detection_loop, daemon=True)
                    self._detection_thread.start()
                    self.logger.info(f"Kaldi wake word detection started at alt rate {alt_rate}")
                    return True
                except Exception as exc2:
                    if self.debug_log:
                        self.logger.debug(f"Alt rate {alt_rate} failed: {exc2}")
                    try:
                        if self.audio_stream:
                            self.audio_stream.stop_stream()
                            self.audio_stream.close()
                    except Exception:
                        pass
                    self.audio_stream = None
            self.cleanup()
            return False

    def stop_detection(self):
        if not self.is_listening:
            return

        self.is_listening = False
        thread = self._detection_thread
        if thread and thread.is_alive():
            thread.join(timeout=2.0)
        self._detection_thread = None

        if self.audio_stream:
            try:
                self.audio_stream.stop_stream()
                self.audio_stream.close()
            except Exception:
                pass
            self.audio_stream = None

        if self.recognizer and self.model:
            self._create_recognizer()

        self.logger.info("Kaldi wake word detection stopped")

    def cleanup(self):
        try:
            self.stop_detection()
        except Exception:
            pass

        if self.audio_interface:
            try:
                self.audio_interface.terminate()
            except Exception:
                pass
            self.audio_interface = None

        self.audio_stream = None
        self.recognizer = None

        if self._owns_model:
            self.model = None
        else:
            self.model = self._shared_model

    # ------------------------------------------------------------------
    # Detection loop
    # ------------------------------------------------------------------
    def _detection_loop(self):
        if not self.audio_stream or not self.recognizer:
            return

        self.logger.debug("Kaldi wake word loop started")
        try:
            while self.is_listening and self.audio_stream and self.recognizer:
                try:
                    data = self.audio_stream.read(self.chunk_size, exception_on_overflow=False)
                except Exception as exc:
                    if self.is_listening:
                        self.logger.debug(f"Kaldi wake word audio read error: {exc}")
                    time.sleep(0.05)
                    continue

                if not data:
                    continue

                try:
                    triggered = False
                    if self.recognizer.AcceptWaveform(data):
                        result = json.loads(self.recognizer.Result())
                        text = result.get("text", "")
                        if self.debug_log and text:
                            self.logger.debug(f"Kaldi full: {text}")
                        triggered = self._check_transcript(text)
                    else:
                        partial = json.loads(self.recognizer.PartialResult())
                        ptext = partial.get("partial", "")
                        if self.debug_log and ptext:
                            self.logger.debug(f"Kaldi partial: {ptext}")
                        triggered = self._check_transcript(ptext)

                    if triggered:
                        now = time.time()
                        if now - self._last_trigger_ts >= self.cooldown_sec:
                            self._last_trigger_ts = now
                            self.logger.info("Kaldi wake word detected")
                            try:
                                self.wake_word_detected.emit()
                            except Exception as exc:
                                self.logger.debug(f"Failed to emit wake word signal: {exc}")
                            self._create_recognizer()
                        else:
                            self.logger.debug("Wake word ignored due to cooldown")

                except Exception as exc:
                    if self.is_listening:
                        self.logger.debug(f"Kaldi wake word recognition error: {exc}")
                    time.sleep(0.05)
        finally:
            self.logger.debug("Kaldi wake word loop ended")

    def _check_transcript(self, text: str) -> bool:
        if not text:
            return False
        normalized = self._normalize_phrase(text)
        if not normalized:
            return False
        # Быстрая проверка: подстрока
        for variant in self._wake_variants:
            if variant in normalized:
                return True
        # Нестрогая проверка по словам с расстоянием Левенштейна
        tokens = normalized.split()
        for token in tokens:
            for variant in self._wake_variants:
                if self._levenshtein_distance(token, variant) <= self._fuzzy_max_distance:
                    return True
        return False

    @staticmethod
    def _levenshtein_distance(a: str, b: str) -> int:
        """Классический алгоритм Левенштейна (O(len(a)*len(b)))."""
        if a == b:
            return 0
        if len(a) == 0:
            return len(b)
        if len(b) == 0:
            return len(a)
        # Инициализация DP-таблицы
        prev = list(range(len(b) + 1))
        for i, ca in enumerate(a, 1):
            cur = [i]
            for j, cb in enumerate(b, 1):
                cost = 0 if ca == cb else 1
                cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + cost))  # удаление  # вставка  # замена
            prev = cur
        return prev[-1]

    @staticmethod
    def _normalize_phrase(text: str) -> str:
        return " ".join(text.strip().lower().split())

    # ------------------------------------------------------------------
    # Mutators
    # ------------------------------------------------------------------
    def set_wake_word(self, wake_word: str):
        wake_word = wake_word.strip()
        if not wake_word:
            return

        was_listening = self.is_listening
        if was_listening:
            self.stop_detection()

        self._base_wake_word = wake_word
        self.config.set("stt.wake_word", wake_word)
        self._wake_variants = self._build_variant_list(self._wake_variants)
        self._create_recognizer()

        if was_listening:
            self.start_detection()

    def update_variants(self, variants: List[str]):
        was_listening = self.is_listening
        if was_listening:
            self.stop_detection()

        self._wake_variants = self._build_variant_list(variants)
        try:
            self.config.set("stt.kaldi_wake_words", self._wake_variants)
        except Exception:
            pass
        self._create_recognizer()

        if was_listening:
            self.start_detection()
