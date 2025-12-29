"""
SAPI5 TTS Engine - Windows system TTS (fallback)
SAPI5 TTS Движок - встроенный синтез речи Windows (fallback)

Используется как финальный fallback когда Silero и Bark недоступны.
Поддерживает:
- pyttsx3 (кроссплатформенный, удобный API)
- win32com SAPI (прямое обращение к Windows API)
- Встроенные голоса Windows
"""

import os
import sys
from pathlib import Path
from typing import Optional, Dict, Any

# Setup path for imports
project_root = Path(__file__).parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from config.config import Config
from modules.tts_base import TTSEngineBase, HealthCheckResult
from utils.logger import ModuleLogger


class SAPITTSEngine(TTSEngineBase):
    """SAPI5 TTS engine for Windows (system text-to-speech)
    
    Fallback engine для озвучки текста на Windows.
    Использует встроенный синтез речи Windows через:
    1. pyttsx3 (если установлен) - удобный API
    2. win32com SAPI (если доступна) - прямое API Windows
    
    Голоса берутся из системных настроек Windows.
    """

    def __init__(self, config: Config, logger: Optional[ModuleLogger] = None):
        """Initialize SAPI TTS engine
        
        Args:
            config: Application configuration
            logger: Optional logger instance
        """
        super().__init__(config, logger or ModuleLogger("SAPITTSEngine"))
        
        self.engine: Any = None
        self.is_ready_flag = False
        self.is_speaking = False
        self.is_windows = os.name == "nt"
        # Align with other TTS engines API
        try:
            self.tts_enabled = bool(config.get("tts.enabled", True))
        except Exception:
            self.tts_enabled = True
        try:
            self.tts_mode = str(config.get("tts.mode", "realtime") or "realtime")
        except Exception:
            self.tts_mode = "realtime"
        # For unified status in factory/tests
        try:
            self.engine_name = "sapi"
        except Exception:
            pass
        
        # Voice settings
        self.voice = config.get("tts.sapi.voice", None)
        rate_val = config.get("tts.sapi.rate", 150)
        if isinstance(rate_val, (int, float, str)):
            try:
                self.rate = int(float(rate_val))
            except Exception:
                self.rate = 150
        else:
            self.rate = 150
        vol_val = config.get("tts.sapi.volume", 100)
        if isinstance(vol_val, (int, float, str)):
            try:
                self.volume = int(float(vol_val))
            except Exception:
                self.volume = 100
        else:
            self.volume = 100
        
        # TTS settings
        self.text_buffer = ""
        self.min_buffer_size = 20
        self.word_boundary_chars = [" ", ".", ",", "!", "?", ";", ":", "\n", "\t"]
        
        # Initialize
        self._init_sapi()
    
    def _init_sapi(self):
        """Initialize SAPI TTS engine"""
        if not self.is_windows:
            self.logger.warning("SAPI is Windows-only")
            self.is_ready_flag = False
            return
        
        try:
            self.logger.info("Initializing SAPI5 TTS...")
            
            # Try pyttsx3 first (more stable)
            try:
                import pyttsx3
                self.engine = pyttsx3.init()
                self.engine.setProperty('rate', int(self.rate))
                self.engine.setProperty('volume', float(self.volume) / 100.0)
                
                if self.voice:
                    try:
                        self.engine.setProperty('voice', self.voice)
                    except Exception:
                        self.logger.warning(f"Voice {self.voice} not available, using default")
                
                self.is_ready_flag = True
                self.logger.info("✓ SAPI5 initialized via pyttsx3")
                return
                
            except ImportError:
                self.logger.debug("pyttsx3 not available, trying win32com")
            except Exception as pyttsx_err:
                self.logger.warning(f"pyttsx3 initialization failed: {pyttsx_err}")
            
            # Fallback: try win32com
            try:
                import win32com.client as wincl
                self.engine = wincl.Dispatch("SAPI.SpVoice")
                
                if hasattr(self.engine, 'Rate'):
                    # pyttsx3 rate is 50-200, SAPI rate is -10 to 10
                    # Convert: 150 (center) → 0, 50 (slow) → -10, 200 (fast) → 10
                    sapi_rate = (int(self.rate) - 125) / 7.5
                    self.engine.Rate = int(sapi_rate)
                
                if hasattr(self.engine, 'Volume'):
                    self.engine.Volume = self.volume
                
                self.is_ready_flag = True
                self.logger.info("✓ SAPI5 initialized via win32com")
                return
                
            except ImportError:
                self.logger.warning("win32com not available (run: pip install pywin32)")
            except Exception as win32_err:
                self.logger.warning(f"win32com initialization failed: {win32_err}")
        
        except Exception as e:
            self.logger.error(f"SAPI5 initialization error: {e}")
            self.is_ready_flag = False

    def speak(self, text: str, voice: Optional[str] = None):
        """Convert text to speech and play it
        
        Args:
            text: Text to synthesize
            voice: Optional voice name (ignored for SAPI, uses system voice)
        """
        # Respect global TTS enable flag
        if not getattr(self, "tts_enabled", True):
            self.logger.debug("SAPI TTS disabled by settings, skipping speech")
            return

        if not text or not text.strip():
            return
        
        if not self.is_ready_flag:
            self.logger.warning("SAPI5 not ready")
            return
        
        if self.engine is None:
            self.logger.error("SAPI5 engine not initialized")
            return
        
        try:
            self.is_speaking = True
            self.logger.debug(f"Speaking via SAPI: {text[:50]}...")
            
            # Use pyttsx3 if available
            if hasattr(self.engine, 'say'):
                self.engine.say(text)
                self.engine.runAndWait()
            # Fallback to win32com
            else:
                self.engine.Speak(text)
            
            self.is_speaking = False
            self.logger.debug("✓ SAPI speech completed")
            try:
                self.playback_finished.emit()
            except Exception:
                pass
            
        except Exception as e:
            self.logger.error(f"SAPI speech error: {e}")
            self.is_speaking = False

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

    # --- Compatibility API used by tests/factory ---
    def synthesize(self, text: str, output_path: Optional[str] = None) -> bool:
        """Synthesize speech and optionally save to file.

        Args:
            text: Text to synthesize
            output_path: Optional WAV file path to save result

        Returns:
            True on success, False otherwise
        """
        try:
            if not text or not text.strip():
                return False

            if not self.is_ready():
                self.logger.warning("SAPI5 not ready")
                return False

            if output_path:
                # Prefer pyttsx3 save_to_file when available
                if hasattr(self.engine, "save_to_file"):
                    try:
                        self.engine.setProperty('rate', int(self.rate))
                        # pyttsx3 volume expects 0.0-1.0
                        self.engine.setProperty('volume', float(self.volume) / 100.0)
                        if self.voice:
                            try:
                                self.engine.setProperty('voice', self.voice)
                            except Exception:
                                pass
                        self.engine.save_to_file(text, str(output_path))
                        self.engine.runAndWait()
                        return True
                    except Exception as e:
                        self.logger.warning(f"pyttsx3 save_to_file failed: {e}")

                # Fallback to win32com SAPI file synthesis
                try:
                    import win32com.client as wincl
                    speaker = wincl.Dispatch("SAPI.SpVoice")
                    stream = wincl.Dispatch("SAPI.SpFileStream")
                    # Create/open file stream
                    from comtypes.gen import SpeechLib  # type: ignore
                    stream.Open(str(output_path), SpeechLib.SSFMCreateForWrite)
                    # Optional: set format (default is often acceptable)
                    speaker.AudioOutputStream = stream
                    speaker.Speak(text)
                    stream.Close()
                    return True
                except Exception as e:
                    self.logger.error(f"win32com file synthesis failed: {e}")
                    return False

            # No output path requested: just speak
            self.speak(text)
            return True

        except Exception as e:
            self.logger.error(f"SAPI synthesize error: {e}")
            return False

    def stop(self):
        """Stop current TTS playback"""
        try:
            if self.engine is not None:
                # pyttsx3
                if hasattr(self.engine, 'stop'):
                    self.engine.stop()
                # win32com - нет встроенного stop, но можем остановить
                
            self.is_speaking = False
            self.logger.debug("SAPI speech stopped")
            try:
                self.playback_finished.emit()
            except Exception:
                pass
            
        except Exception as e:
            self.logger.error(f"Error stopping SAPI: {e}")

    def flush_buffer(self, voice: Optional[str] = None):
        """Flush remaining text in buffer
        
        Args:
            voice: Optional voice name
        """
        if self.text_buffer.strip():
            self.speak(self.text_buffer.strip(), voice)
            self.text_buffer = ""

    def is_ready(self) -> bool:
        """Check if TTS engine is ready"""
        return self.is_ready_flag and self.engine is not None

    def health_check(self) -> HealthCheckResult:
        """Check TTS engine health
        
        Returns:
            HealthCheckResult with health status
        """
        try:
            if not self.is_windows:
                return HealthCheckResult(
                    healthy=False,
                    message="SAPI5 only available on Windows",
                    details={"os": os.name}
                )
            
            if not self.is_ready_flag:
                return HealthCheckResult(
                    healthy=False,
                    message="SAPI5 not initialized",
                    details={"error": "Initialization failed"}
                )
            
            if self.engine is None:
                return HealthCheckResult(
                    healthy=False,
                    message="SAPI5 engine is None",
                    details={"error": "Engine not created"}
                )
            
            # Avoid audible tests; consider healthy if engine object exists
            return HealthCheckResult(
                healthy=True,
                message="SAPI5 ready",
                details={"rate": self.rate, "volume": self.volume}
            )
        
        except Exception as e:
            return HealthCheckResult(
                healthy=False,
                message=f"Health check error: {str(e)[:100]}",
                details={"error": str(e)[:100]}
            )

    def get_available_voices(self) -> list:
        """Get list of available voices from Windows
        
        Returns:
            List of voice names
        """
        voices = []
        
        try:
            if hasattr(self.engine, 'getProperty'):
                # pyttsx3 API
                voices = self.engine.getProperty('voices')
                return [v.id for v in voices] if voices else []
            
            elif self.engine is not None:
                # win32com API
                try:
                    import win32com.client as wincl
                    voice_obj = wincl.Dispatch("SAPI.SpObjectTokens")
                    voice_tokens = voice_obj.Enumerate("HKEY_LOCAL_MACHINE\\SOFTWARE\\Microsoft\\Speech\\Voices")
                    
                    for token in voice_tokens:
                        voices.append(token.GetAttribute("Name") or "Unknown")
                    
                    return voices
                
                except Exception as e:
                    self.logger.debug(f"Failed to enumerate win32com voices: {e}")
        
        except Exception as e:
            self.logger.warning(f"Failed to get available voices: {e}")
        
        # Fallback: return common Windows voices
        return ["Microsoft Irina Desktop", "Microsoft Zira Desktop", "Microsoft David Desktop"]

    def set_voice(self, voice: str) -> bool:
        """Set active voice
        
        Args:
            voice: Voice name
            
        Returns:
            True if voice was set, False otherwise
        """
        try:
            if self.engine is None:
                return False
            
            if hasattr(self.engine, 'setProperty'):
                # pyttsx3 API
                self.engine.setProperty('voice', voice)
            else:
                # win32com API
                self.engine.Voice = voice
            
            self.voice = voice
            self.config.set("tts.sapi.voice", voice)
            self.logger.info(f"Voice set to: {voice}")
            return True
            
        except Exception as e:
            self.logger.warning(f"Failed to set voice {voice}: {e}")
            return False

    def set_rate(self, rate: int) -> bool:
        """Set speech rate
        
        Args:
            rate: Rate 50-200 for pyttsx3, or -10 to 10 for win32com
            
        Returns:
            True if rate was set
        """
        try:
            if self.engine is None:
                return False
            
            if hasattr(self.engine, 'setProperty'):
                # pyttsx3 API
                self.engine.setProperty('rate', rate)
            else:
                # win32com API - convert 50-200 to -10 to 10
                sapi_rate = (rate - 125) / 7.5
                self.engine.Rate = int(sapi_rate)
            
            self.rate = rate
            self.config.set("tts.sapi.rate", rate)
            return True
            
        except Exception as e:
            self.logger.warning(f"Failed to set rate {rate}: {e}")
            return False

    def set_volume(self, volume: int) -> bool:
        """Set volume
        
        Args:
            volume: Volume 0-100
            
        Returns:
            True if volume was set
        """
        try:
            if self.engine is None:
                return False
            
            if hasattr(self.engine, 'setProperty'):
                # pyttsx3 API (0.0-1.0)
                self.engine.setProperty('volume', volume / 100.0)
            else:
                # win32com API (0-100)
                self.engine.Volume = volume
            
            self.volume = volume
            self.config.set("tts.sapi.volume", volume)
            return True
            
        except Exception as e:
            self.logger.warning(f"Failed to set volume {volume}: {e}")
            return False

    def get_status(self) -> Dict[str, Any]:
        """Get TTS engine status
        
        Returns:
            Status dictionary
        """
        return {
            "engine": "sapi",
            "ready": self.is_ready(),
            "speaking": self.is_speaking,
            "windows": self.is_windows,
            "rate": self.rate,
            "volume": self.volume,
            "voice": self.voice or "default",
            "available_voices": self.get_available_voices(),
        }

    def set_mode(self, mode: str):
        """Set TTS mode (for compatibility with SileroTTSEngine)
        
        Args:
            mode: Mode name (realtime, sentence_by_sentence, after_complete)
        """
        self.logger.debug(f"TTS mode requested: {mode} (SAPI doesn't have modes)")

    def set_enabled(self, enabled: bool):
        """Enable or disable TTS (for compatibility)
        
        Args:
            enabled: True to enable, False to disable
        """
        try:
            self.tts_enabled = bool(enabled)
            self.logger.info(f"SAPI TTS {'enabled' if self.tts_enabled else 'disabled'}")
        except Exception:
            self.logger.debug(f"TTS enable requested: {enabled} (SAPI manages this internally)")
