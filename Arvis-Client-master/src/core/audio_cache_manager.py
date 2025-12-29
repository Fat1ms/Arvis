import os
from pathlib import Path
from typing import Dict, Optional
from config.config import Config
from modules.tts_base import TTSEngineBase
from utils.logger import ModuleLogger
from i18n import I18N

class AudioCacheManager:
    """
    Manages pre-generated audio responses for the Compact Mode.
    Generates audio files using the current TTS engine and language.
    """
    
    def __init__(self, config: Config, tts_engine: TTSEngineBase):
        self.config = config
        self.tts_engine = tts_engine
        self.logger = ModuleLogger("AudioCacheManager")
        self.cache_dir = Path("data/cache/audio")
        
        # Phrases to generate with translations
        self.phrases = {
            "listening": {
                "ru": "Слушаю",
                "en": "Listening"
            },
            "done": {
                "ru": "Готово",
                "en": "Done"
            },
            "error": {
                "ru": "Ошибка",
                "en": "Error"
            },
            "executing": {
                "ru": "Выполняю",
                "en": "Executing"
            },
            "cant_chat": {
                "ru": "В этом режиме я выполняю только команды",
                "en": "I only execute commands in this mode"
            },
            "ready": {
                "ru": "Система готова",
                "en": "System ready"
            }
        }

    def ensure_cache(self):
        """Ensure all phrases are generated for current language and engine"""
        try:
            lang = I18N.get().lang
            # Fallback to 'en' if lang not in phrases, or just use 'ru' as default
            if lang not in ["ru", "en"]:
                lang = "en"
                
            engine_name = self.tts_engine.__class__.__name__
            
            # Path: data/cache/audio/{lang}/{engine_name}/
            path = self.cache_dir / lang / engine_name
            path.mkdir(parents=True, exist_ok=True)
            
            for key, translations in self.phrases.items():
                text = translations.get(lang, translations.get("en", "Error"))
                file_path = path / f"{key}.wav"
                
                if not file_path.exists():
                    self.logger.info(f"Generating cached audio for '{key}' ({text})...")
                    # Use the engine to save to file
                    # Note: We assume save_to_file is implemented in the engine
                    if hasattr(self.tts_engine, "save_to_file"):
                        success = self.tts_engine.save_to_file(text, str(file_path))
                        if not success:
                            self.logger.error(f"Failed to generate audio for {key}")
                    else:
                        self.logger.warning(f"TTS Engine {engine_name} does not support save_to_file")
        except Exception as e:
            self.logger.error(f"Error ensuring audio cache: {e}")

    def get_audio_path(self, key: str) -> Optional[str]:
        """Get path to cached audio file"""
        try:
            lang = I18N.get().lang
            if lang not in ["ru", "en"]:
                lang = "en"
                
            engine_name = self.tts_engine.__class__.__name__
            path = self.cache_dir / lang / engine_name / f"{key}.wav"
            
            if path.exists():
                return str(path)
            return None
        except Exception:
            return None
