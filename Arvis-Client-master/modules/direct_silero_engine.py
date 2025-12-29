"""Alternative TTS engine using direct Silero model loading without torch.hub"""

import io
import json
from pathlib import Path
from typing import Any, Optional, Union

import numpy as np
import sounddevice as sd
import soundfile as sf
import torch
from omegaconf import OmegaConf

import sys
if str(Path(__file__).parent.parent) not in sys.path:
    sys.path.insert(0, str(Path(__file__).parent.parent))

from modules.tts_base import TTSEngineBase, HealthCheckResult


class DirectSileroTTSEngine(TTSEngineBase):
    """Direct Silero TTS without torch.hub"""
    
    def __init__(self, config, logger=None):
        super().__init__(config, logger)
        self.model = None
        self.is_ready_flag = False
        self.sample_rate = config.get("tts.sample_rate", 48000)
        self.voice = config.get("tts.voice", "aidar")
        self.device = config.get("tts.device", "cpu")
        self._load_model_direct()
    
    def _load_model_direct(self):
        """Load Silero model directly without torch.hub"""
        try:
            print("[DirectSilero] Loading model directly...")
            
            # Download model from GitHub release
            model_url = "https://github.com/snakers4/silero-models/releases/download/models_ts_v2/model_v2_ru.pt"
            config_url = "https://github.com/snakers4/silero-models/releases/download/models_ts_v2/model_v2.yaml"
            
            # Get cache directory
            cache_dir = Path.home() / ".cache" / "silero-tts-direct"
            cache_dir.mkdir(parents=True, exist_ok=True)
            
            model_path = cache_dir / "model_v2_ru.pt"
            config_path = cache_dir / "model_v2.yaml"
            
            # Download model if not cached
            if not model_path.exists():
                print(f"[DirectSilero] Downloading model from {model_url}...")
                import urllib.request
                urllib.request.urlretrieve(model_url, model_path)
                print(f"[DirectSilero] Model saved to {model_path}")
            
            if not config_path.exists():
                print(f"[DirectSilero] Downloading config from {config_url}...")
                import urllib.request
                urllib.request.urlretrieve(config_url, config_path)
                print(f"[DirectSilero] Config saved to {config_path}")
            
            # Load model
            print(f"[DirectSilero] Loading model from {model_path}...")
            self.model = torch.jit.load(str(model_path), map_location=self.device)
            self.model.eval()
            
            # Load config
            with open(config_path) as f:
                self.config_dict = OmegaConf.to_container(OmegaConf.load(config_path))
            
            self.is_ready_flag = True
            print("[DirectSilero] Model loaded successfully")
            
        except Exception as e:
            print(f"[DirectSilero] Error loading model: {e}")
            import traceback
            traceback.print_exc()
            self.model = None
            self.is_ready_flag = False
    
    def speak(self, text: str, voice: Optional[str] = None):
        """Synthesize and play text"""
        if not self.is_ready():
            print("[DirectSilero] Model not ready")
            return
        if self.model is None:
            print("[DirectSilero] Model is None")
            return
        
        voice = voice or self.voice
        print(f"[DirectSilero] Synthesizing: {text[:50]}... with voice {voice}")
        
        try:
            # Prepare input
            text_tensor = torch.tensor([self._text_to_tokens(text)])
            
            # Synthesize
            with torch.no_grad():
                audio = self.model.apply_tts(
                    text=text,
                    speaker=voice,
                    sample_rate=self.sample_rate
                )
            
            if audio is not None:
                # Convert to numpy
                if torch.is_tensor(audio):
                    audio = audio.cpu().numpy()
                
                # Play audio
                print(f"[DirectSilero] Playing audio ({len(audio)} samples)")
                sd.play(audio, samplerate=self.sample_rate)
                sd.wait()
                try:
                    self.playback_finished.emit()
                except Exception:
                    pass
        
        except Exception as e:
            print(f"[DirectSilero] Error synthesizing: {e}")
            import traceback
            traceback.print_exc()

    def speak_streaming(self, text_chunk: str, voice: Optional[str] = None):
        """Simple streaming: bufferless immediate speak for chunks"""
        if text_chunk and text_chunk.strip():
            self.speak(text_chunk, voice)
    
    def _text_to_tokens(self, text: str):
        """Convert text to token indices (placeholder)"""
        # Simplified implementation - real one would use proper tokenizer
        return list(range(len(text)))
    
    def is_ready(self) -> bool:
        return self.is_ready_flag
    
    def stop(self):
        sd.stop()
        try:
            self.playback_finished.emit()
        except Exception:
            pass
    
    def health_check(self) -> HealthCheckResult:
        if self.is_ready():
            return HealthCheckResult(healthy=True, message="Direct Silero TTS ready")
        return HealthCheckResult(healthy=False, message="Direct Silero TTS not ready")


if __name__ == "__main__":
    from config.config import Config
    from utils.logger import ModuleLogger
    
    config = Config(str(Path(__file__).parent.parent / "config" / "config.json"))
    logger = ModuleLogger("TestDirectSilero")
    
    engine = DirectSileroTTSEngine(config, logger)
    print(f"Ready: {engine.is_ready()}")
    
    if engine.is_ready():
        engine.speak("Привет, это прямая загрузка модели Silero")
