"""
Voice Models Manager - STT (Vosk) and TTS (Silero, Piper, Kokoro, StyleTTS2, F5-TTS) model management
"""

from __future__ import annotations

import io
import os
import shutil
import urllib.request
import zipfile
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Optional, List, Dict, Callable, Any

from PyQt6.QtCore import QObject, QThread, pyqtSignal


class ModelType(Enum):
    """Type of voice model"""
    STT = "stt"  # Speech-to-Text (Vosk)
    TTS = "tts"  # Text-to-Speech (Silero, Piper, Kokoro, StyleTTS2, F5-TTS)


@dataclass
class VoiceModel:
    """Voice model info"""
    name: str
    display_name: str
    model_type: ModelType
    language: str
    url: str
    size: str  # Human-readable size
    is_installed: bool = False
    local_path: Optional[Path] = None


# Available Vosk STT models
VOSK_MODELS: List[VoiceModel] = [
    # Russian
    VoiceModel(
        name="vosk-model-small-ru-0.22",
        display_name="Русский (компактная)",
        model_type=ModelType.STT,
        language="ru",
        url="https://alphacephei.com/vosk/models/vosk-model-small-ru-0.22.zip",
        size="45 MB"
    ),
    VoiceModel(
        name="vosk-model-ru-0.42",
        display_name="Русский (полная)",
        model_type=ModelType.STT,
        language="ru",
        url="https://alphacephei.com/vosk/models/vosk-model-ru-0.42.zip",
        size="1.8 GB"
    ),
    # English
    VoiceModel(
        name="vosk-model-small-en-us-0.15",
        display_name="English (compact)",
        model_type=ModelType.STT,
        language="en",
        url="https://alphacephei.com/vosk/models/vosk-model-small-en-us-0.15.zip",
        size="40 MB"
    ),
    VoiceModel(
        name="vosk-model-en-us-0.22",
        display_name="English (full)",
        model_type=ModelType.STT,
        language="en",
        url="https://alphacephei.com/vosk/models/vosk-model-en-us-0.22.zip",
        size="1.8 GB"
    ),
    # Ukrainian
    VoiceModel(
        name="vosk-model-small-uk-v3-small",
        display_name="Українська (компактна)",
        model_type=ModelType.STT,
        language="uk",
        url="https://alphacephei.com/vosk/models/vosk-model-small-uk-v3-small.zip",
        size="50 MB"
    ),
    # Spanish
    VoiceModel(
        name="vosk-model-small-es-0.42",
        display_name="Español (compacto)",
        model_type=ModelType.STT,
        language="es",
        url="https://alphacephei.com/vosk/models/vosk-model-small-es-0.42.zip",
        size="39 MB"
    ),
]

# Available Silero TTS models (auto-downloaded by torch.hub)
SILERO_MODELS: List[VoiceModel] = [
    VoiceModel(
        name="silero_tts_ru",
        display_name="Silero TTS Русский",
        model_type=ModelType.TTS,
        language="ru",
        url="",  # Auto-downloaded via torch.hub
        size="~100 MB"
    ),
    VoiceModel(
        name="silero_tts_en",
        display_name="Silero TTS English",
        model_type=ModelType.TTS,
        language="en",
        url="",
        size="~100 MB"
    ),
    VoiceModel(
        name="silero_tts_de",
        display_name="Silero TTS Deutsch",
        model_type=ModelType.TTS,
        language="de",
        url="",
        size="~100 MB"
    ),
]

# Available Piper TTS models (fast, high-quality offline TTS)
PIPER_MODELS: List[VoiceModel] = [
    VoiceModel(
        name="piper_ru_irina",
        display_name="Piper Ирина (RU)",
        model_type=ModelType.TTS,
        language="ru",
        url="https://huggingface.co/rhasspy/piper-voices/resolve/main/ru/ru_RU/irina/medium/ru_RU-irina-medium.onnx",
        size="~60 MB"
    ),
    VoiceModel(
        name="piper_ru_dmitri",
        display_name="Piper Дмитрий (RU)",
        model_type=ModelType.TTS,
        language="ru",
        url="https://huggingface.co/rhasspy/piper-voices/resolve/main/ru/ru_RU/dmitri/medium/ru_RU-dmitri-medium.onnx",
        size="~60 MB"
    ),
    VoiceModel(
        name="piper_en_lessac",
        display_name="Piper Lessac (EN)",
        model_type=ModelType.TTS,
        language="en",
        url="https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/lessac/medium/en_US-lessac-medium.onnx",
        size="~60 MB"
    ),
    VoiceModel(
        name="piper_en_amy",
        display_name="Piper Amy (EN)",
        model_type=ModelType.TTS,
        language="en",
        url="https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/amy/medium/en_US-amy-medium.onnx",
        size="~60 MB"
    ),
    VoiceModel(
        name="piper_uk",
        display_name="Piper Ukrainian",
        model_type=ModelType.TTS,
        language="uk",
        url="https://huggingface.co/rhasspy/piper-voices/resolve/main/uk/uk_UA/ukrainian_tts/medium/uk_UA-ukrainian_tts-medium.onnx",
        size="~60 MB"
    ),
    VoiceModel(
        name="piper_de_thorsten",
        display_name="Piper Thorsten (DE)",
        model_type=ModelType.TTS,
        language="de",
        url="https://huggingface.co/rhasspy/piper-voices/resolve/main/de/de_DE/thorsten/medium/de_DE-thorsten-medium.onnx",
        size="~60 MB"
    ),
    VoiceModel(
        name="piper_es_davefx",
        display_name="Piper Dave (ES)",
        model_type=ModelType.TTS,
        language="es",
        url="https://huggingface.co/rhasspy/piper-voices/resolve/main/es/es_ES/davefx/medium/es_ES-davefx-medium.onnx",
        size="~60 MB"
    ),
]

# Available Kokoro TTS models (high-quality neural TTS)
KOKORO_MODELS: List[VoiceModel] = [
    VoiceModel(
        name="kokoro_en",
        display_name="Kokoro English",
        model_type=ModelType.TTS,
        language="en",
        url="",  # Auto-downloaded via pip install kokoro
        size="~500 MB"
    ),
    VoiceModel(
        name="kokoro_ja",
        display_name="Kokoro Japanese",
        model_type=ModelType.TTS,
        language="ja",
        url="",
        size="~500 MB"
    ),
    VoiceModel(
        name="kokoro_zh",
        display_name="Kokoro Chinese",
        model_type=ModelType.TTS,
        language="zh",
        url="",
        size="~500 MB"
    ),
    VoiceModel(
        name="kokoro_ko",
        display_name="Kokoro Korean",
        model_type=ModelType.TTS,
        language="ko",
        url="",
        size="~500 MB"
    ),
    VoiceModel(
        name="kokoro_fr",
        display_name="Kokoro French",
        model_type=ModelType.TTS,
        language="fr",
        url="",
        size="~500 MB"
    ),
    VoiceModel(
        name="kokoro_es",
        display_name="Kokoro Spanish",
        model_type=ModelType.TTS,
        language="es",
        url="",
        size="~500 MB"
    ),
]

# Available StyleTTS 2 models (state-of-the-art expressive TTS)
STYLETTS2_MODELS: List[VoiceModel] = [
    VoiceModel(
        name="styletts2_ljspeech",
        display_name="StyleTTS2 LJSpeech (EN)",
        model_type=ModelType.TTS,
        language="en",
        url="https://huggingface.co/yl4579/StyleTTS2-LJSpeech",
        size="~300 MB"
    ),
    VoiceModel(
        name="styletts2_libritts",
        display_name="StyleTTS2 LibriTTS (EN)",
        model_type=ModelType.TTS,
        language="en",
        url="https://huggingface.co/yl4579/StyleTTS2-LibriTTS",
        size="~500 MB"
    ),
]

# Available F5-TTS / E2-TTS models (zero-shot voice cloning)
F5TTS_MODELS: List[VoiceModel] = [
    VoiceModel(
        name="f5tts_base",
        display_name="F5-TTS Base (EN/ZH)",
        model_type=ModelType.TTS,
        language="multi",
        url="",  # Auto-downloaded via pip install f5-tts
        size="~1.2 GB"
    ),
    VoiceModel(
        name="e2tts_base",
        display_name="E2-TTS Base (Fast)",
        model_type=ModelType.TTS,
        language="multi",
        url="",
        size="~800 MB"
    ),
]

# All TTS models combined
ALL_TTS_MODELS: List[VoiceModel] = SILERO_MODELS + PIPER_MODELS + KOKORO_MODELS + STYLETTS2_MODELS + F5TTS_MODELS

# TTS Engine types for selection
TTS_ENGINES = {
    "silero": {
        "name": "Silero",
        "description": "Быстрый офлайн TTS (русский, английский, немецкий)",
        "languages": ["ru", "en", "de"],
        "models": SILERO_MODELS,
    },
    "piper": {
        "name": "Piper",
        "description": "Очень быстрый офлайн TTS с множеством голосов",
        "languages": ["ru", "en", "uk", "de", "es"],
        "models": PIPER_MODELS,
    },
    "kokoro": {
        "name": "Kokoro",
        "description": "Высококачественный нейросетевой TTS",
        "languages": ["en", "ja", "zh", "ko", "fr", "es"],
        "models": KOKORO_MODELS,
    },
    "styletts2": {
        "name": "StyleTTS 2",
        "description": "Экспрессивный TTS с передачей стиля",
        "languages": ["en"],
        "models": STYLETTS2_MODELS,
    },
    "f5tts": {
        "name": "F5-TTS / E2-TTS",
        "description": "Zero-shot клонирование голоса",
        "languages": ["en", "zh", "multi"],
        "models": F5TTS_MODELS,
    },
}


class DownloadWorker(QThread):
    """Worker thread for downloading models"""
    
    progress = pyqtSignal(int, str)  # percent, message
    finished = pyqtSignal(bool, str, object)  # success, message, model
    
    def __init__(self, model: VoiceModel, target_dir: Path):
        super().__init__()
        self.model = model
        self.target_dir = target_dir
    
    def run(self):
        try:
            self.progress.emit(0, f"Скачивание {self.model.display_name}...")
            
            # Download
            req = urllib.request.Request(
                self.model.url,
                headers={"User-Agent": "ArvisLauncher/1.0"}
            )
            
            with urllib.request.urlopen(req, timeout=60) as resp:
                total = int(resp.headers.get("Content-Length", 0))
                downloaded = 0
                chunks = []
                
                while True:
                    chunk = resp.read(8192)
                    if not chunk:
                        break
                    chunks.append(chunk)
                    downloaded += len(chunk)
                    
                    if total > 0:
                        pct = int(downloaded / total * 100)
                        self.progress.emit(pct, f"Скачивание... {downloaded // 1024 // 1024} MB")
                
                data = b"".join(chunks)
            
            self.progress.emit(100, "Распаковка...")
            
            # Extract
            self.target_dir.mkdir(parents=True, exist_ok=True)
            
            with zipfile.ZipFile(io.BytesIO(data)) as zf:
                # Find root folder name in archive
                names = zf.namelist()
                root_folder = names[0].split("/")[0] if names else self.model.name
                
                zf.extractall(self.target_dir)
                
                extracted_path = self.target_dir / root_folder
            
            self.model.is_installed = True
            self.model.local_path = extracted_path
            
            self.finished.emit(True, f"Модель {self.model.display_name} установлена", self.model)
            
        except Exception as e:
            self.finished.emit(False, f"Ошибка: {e}", self.model)


class VoiceModelsManager(QObject):
    """Manager for STT/TTS voice models"""
    
    # Signals
    models_updated = pyqtSignal(list)  # List[VoiceModel]
    progress = pyqtSignal(int, str)
    operation_finished = pyqtSignal(bool, str)
    log_line = pyqtSignal(str)
    
    def __init__(self, models_dir: Path, parent: Optional[QObject] = None):
        super().__init__(parent)
        self.models_dir = Path(models_dir)
        self._workers: List[DownloadWorker] = []
        
        # Scan for installed models
        self._scan_installed()
    
    def _scan_installed(self):
        """Scan models directory for installed models"""
        if not self.models_dir.exists():
            return
        
        for model in VOSK_MODELS:
            model_path = self.models_dir / model.name
            if model_path.exists() and model_path.is_dir():
                model.is_installed = True
                model.local_path = model_path
            else:
                model.is_installed = False
                model.local_path = None
        
        # Check Silero (typically in torch cache)
        torch_cache = Path.home() / ".cache" / "torch" / "hub"
        for model in SILERO_MODELS:
            # Silero models are stored in torch hub cache
            model.is_installed = (torch_cache / "snakers4_silero-models_master").exists()
        
        # Check Piper models
        piper_dir = self.models_dir / "piper"
        for model in PIPER_MODELS:
            # Piper models are .onnx files
            model_name = model.name.replace("piper_", "").replace("_", "-")
            model_path = piper_dir / f"{model_name}.onnx"
            model.is_installed = model_path.exists()
            model.local_path = model_path if model.is_installed else None
        
        # Check Kokoro (pip package)
        try:
            import kokoro
            for model in KOKORO_MODELS:
                model.is_installed = True
        except ImportError:
            for model in KOKORO_MODELS:
                model.is_installed = False
        
        # Check StyleTTS2
        styletts2_dir = self.models_dir / "styletts2"
        for model in STYLETTS2_MODELS:
            model_name = model.name.replace("styletts2_", "")
            model_path = styletts2_dir / model_name
            model.is_installed = model_path.exists()
            model.local_path = model_path if model.is_installed else None
        
        # Check F5-TTS (pip package)
        try:
            from f5_tts.api import F5TTS
            for model in F5TTS_MODELS:
                model.is_installed = True
        except ImportError:
            for model in F5TTS_MODELS:
                model.is_installed = False
    
    def get_stt_models(self) -> List[VoiceModel]:
        """Get all STT models"""
        return [m for m in VOSK_MODELS]
    
    def get_tts_models(self) -> List[VoiceModel]:
        """Get all TTS models"""
        return list(ALL_TTS_MODELS)
    
    def get_tts_models_by_engine(self, engine: str) -> List[VoiceModel]:
        """Get TTS models for a specific engine"""
        if engine in TTS_ENGINES:
            return TTS_ENGINES[engine]["models"]
        return []
    
    def get_models_by_language(self, language: str) -> List[VoiceModel]:
        """Get models for a specific language"""
        return [m for m in VOSK_MODELS + ALL_TTS_MODELS if m.language == language]
    
    def get_available_tts_engines(self) -> Dict[str, Any]:
        """Get dictionary of available TTS engines with their info"""
        return TTS_ENGINES
    
    def download_model(self, model: VoiceModel):
        """Download and install a model"""
        if model.model_type == ModelType.TTS:
            # Determine which TTS engine and use appropriate download method
            if model.name.startswith("silero"):
                self._download_silero()
            elif model.name.startswith("piper"):
                self._download_piper(model)
            elif model.name.startswith("kokoro"):
                self._install_kokoro()
            elif model.name.startswith("styletts2"):
                self._download_styletts2(model)
            elif model.name.startswith("f5tts") or model.name.startswith("e2tts"):
                self._install_f5tts()
            return
        
        worker = DownloadWorker(model, self.models_dir)
        worker.progress.connect(self.progress.emit)
        worker.finished.connect(self._on_download_finished)
        self._workers.append(worker)
        worker.start()
    
    def _download_piper(self, model: VoiceModel):
        """Download Piper TTS model"""
        self.progress.emit(0, f"Загрузка {model.display_name}...")
        
        try:
            piper_dir = self.models_dir / "piper"
            piper_dir.mkdir(parents=True, exist_ok=True)
            
            # Download model .onnx file
            if model.url:
                model_name = model.url.split("/")[-1]
                model_path = piper_dir / model_name
                
                req = urllib.request.Request(
                    model.url,
                    headers={"User-Agent": "ArvisLauncher/1.0"}
                )
                
                with urllib.request.urlopen(req, timeout=120) as resp:
                    total = int(resp.headers.get("Content-Length", 0))
                    downloaded = 0
                    
                    with open(model_path, 'wb') as f:
                        while True:
                            chunk = resp.read(8192)
                            if not chunk:
                                break
                            f.write(chunk)
                            downloaded += len(chunk)
                            
                            if total > 0:
                                pct = int(downloaded / total * 100)
                                self.progress.emit(pct, f"Скачивание... {downloaded // 1024 // 1024} MB")
                
                # Download config .onnx.json file
                config_url = model.url + ".json"
                config_path = piper_dir / (model_name + ".json")
                
                try:
                    urllib.request.urlretrieve(config_url, config_path)
                except:
                    pass  # Config is optional
                
                model.is_installed = True
                model.local_path = model_path
                
                self.progress.emit(100, f"{model.display_name} установлен")
                self.operation_finished.emit(True, f"{model.display_name} успешно установлен")
                self.models_updated.emit(self.get_tts_models())
            else:
                self.operation_finished.emit(False, "URL модели не указан")
                
        except Exception as e:
            self.operation_finished.emit(False, f"Ошибка загрузки Piper: {e}")
    
    def _install_kokoro(self):
        """Install Kokoro TTS via pip"""
        self.progress.emit(0, "Установка Kokoro TTS...")
        self.log_line.emit("Выполняется: pip install kokoro>=0.3")
        
        try:
            import subprocess
            import sys
            
            result = subprocess.run(
                [sys.executable, "-m", "pip", "install", "kokoro>=0.3", "kokoro-onnx"],
                capture_output=True,
                text=True,
                timeout=300
            )
            
            if result.returncode == 0:
                for model in KOKORO_MODELS:
                    model.is_installed = True
                
                self.progress.emit(100, "Kokoro TTS установлен")
                self.operation_finished.emit(True, "Kokoro TTS успешно установлен")
                self.models_updated.emit(self.get_tts_models())
            else:
                self.operation_finished.emit(False, f"Ошибка pip: {result.stderr}")
                
        except Exception as e:
            self.operation_finished.emit(False, f"Ошибка установки Kokoro: {e}")
    
    def _download_styletts2(self, model: VoiceModel):
        """Download StyleTTS2 model"""
        self.progress.emit(0, f"Загрузка {model.display_name}...")
        self.log_line.emit("StyleTTS2 требует ручной установки.")
        self.log_line.emit("Инструкции: https://github.com/yl4579/StyleTTS2")
        
        # For now, just inform the user
        self.operation_finished.emit(
            False, 
            "StyleTTS2 требует ручной установки. См. https://github.com/yl4579/StyleTTS2"
        )
    
    def _install_f5tts(self):
        """Install F5-TTS via pip"""
        self.progress.emit(0, "Установка F5-TTS...")
        self.log_line.emit("Выполняется: pip install f5-tts")
        
        try:
            import subprocess
            import sys
            
            result = subprocess.run(
                [sys.executable, "-m", "pip", "install", "f5-tts"],
                capture_output=True,
                text=True,
                timeout=600  # F5-TTS is large
            )
            
            if result.returncode == 0:
                for model in F5TTS_MODELS:
                    model.is_installed = True
                
                self.progress.emit(100, "F5-TTS установлен")
                self.operation_finished.emit(True, "F5-TTS успешно установлен")
                self.models_updated.emit(self.get_tts_models())
            else:
                self.operation_finished.emit(False, f"Ошибка pip: {result.stderr}")
                
        except Exception as e:
            self.operation_finished.emit(False, f"Ошибка установки F5-TTS: {e}")
    
    def _download_silero(self):
        """Download Silero TTS model via torch"""
        self.progress.emit(0, "Загрузка Silero TTS...")
        
        try:
            import torch
            # This will download the model if not present
            torch.hub.load(
                repo_or_dir='snakers4/silero-models',
                model='silero_tts',
                language='ru',
                speaker='v4_ru'
            )
            
            # Mark all Silero models as installed
            for model in SILERO_MODELS:
                model.is_installed = True
            
            self.progress.emit(100, "Silero TTS установлен")
            self.operation_finished.emit(True, "Silero TTS успешно установлен")
            self.models_updated.emit(self.get_tts_models())
            
        except ImportError:
            self.operation_finished.emit(False, "PyTorch не установлен. Установите полные зависимости.")
        except Exception as e:
            self.operation_finished.emit(False, f"Ошибка загрузки Silero: {e}")
    
    def _on_download_finished(self, success: bool, message: str, model: VoiceModel):
        """Handle download completion"""
        self.log_line.emit(message)
        self.operation_finished.emit(success, message)
        
        if success:
            self._scan_installed()
            self.models_updated.emit(self.get_stt_models())
    
    def remove_model(self, model: VoiceModel):
        """Remove an installed model"""
        if not model.local_path or not model.local_path.exists():
            self.operation_finished.emit(False, "Модель не найдена")
            return
        
        try:
            if model.local_path.is_dir():
                shutil.rmtree(model.local_path)
            else:
                model.local_path.unlink()
            
            model.is_installed = False
            model.local_path = None
            
            self.log_line.emit(f"Модель {model.display_name} удалена")
            self.operation_finished.emit(True, f"Модель {model.display_name} удалена")
            self.models_updated.emit(self.get_stt_models())
            
        except Exception as e:
            self.operation_finished.emit(False, f"Ошибка удаления: {e}")
    
    def get_recommended_stt_model(self, language: str) -> Optional[VoiceModel]:
        """Get recommended STT model for language"""
        # Prefer small models
        for model in VOSK_MODELS:
            if model.language == language and "small" in model.name:
                return model
        return None
    
    def get_recommended_tts_engine(self, language: str) -> str:
        """Get recommended TTS engine for language"""
        # Priority: Piper > Silero > Kokoro > F5-TTS > StyleTTS2
        if language in ["ru"]:
            return "piper"  # Piper has good Russian support
        elif language in ["en"]:
            return "silero"  # Silero is fast and reliable for English too
        elif language in ["ja", "zh", "ko"]:
            return "kokoro"  # Kokoro excels at Asian languages
        else:
            return "silero"  # Default fallback    
    def install_tts_engine(self, engine_id: str):
        """Install a TTS engine by ID"""
        self.log_line.emit(f"Установка TTS движка: {engine_id}")
        
        if engine_id == "silero":
            self._download_silero()
        elif engine_id == "piper":
            self._install_piper()
        elif engine_id == "kokoro":
            self._install_kokoro()
        elif engine_id == "styletts2":
            self._install_styletts2()
        elif engine_id == "f5tts":
            self._install_f5tts()
        elif engine_id == "bark":
            self._install_bark()
        else:
            self.operation_finished.emit(False, f"Неизвестный TTS движок: {engine_id}")
    
    def _install_piper(self):
        """Install Piper TTS"""
        self.progress.emit(0, "Установка Piper TTS...")
        self.log_line.emit("Выполняется: pip install piper-tts")
        
        try:
            import subprocess
            import sys
            
            # Install piper-tts package
            result = subprocess.run(
                [sys.executable, "-m", "pip", "install", "piper-tts"],
                capture_output=True,
                text=True,
                timeout=300
            )
            
            if result.returncode == 0:
                self.progress.emit(50, "Piper установлен, скачивание русской модели...")
                
                # Download default Russian model
                piper_dir = self.models_dir / "piper"
                piper_dir.mkdir(parents=True, exist_ok=True)
                
                # Download ru_RU-irina-medium model
                model_url = "https://huggingface.co/rhasspy/piper-voices/resolve/v1.0.0/ru/ru_RU/irina/medium/ru_RU-irina-medium.onnx"
                config_url = "https://huggingface.co/rhasspy/piper-voices/resolve/v1.0.0/ru/ru_RU/irina/medium/ru_RU-irina-medium.onnx.json"
                
                model_path = piper_dir / "ru_RU-irina-medium.onnx"
                config_path = piper_dir / "ru_RU-irina-medium.onnx.json"
                
                try:
                    req = urllib.request.Request(model_url, headers={"User-Agent": "ArvisLauncher/1.0"})
                    with urllib.request.urlopen(req, timeout=120) as resp:
                        total = int(resp.headers.get("Content-Length", 0))
                        downloaded = 0
                        
                        with open(model_path, 'wb') as f:
                            while True:
                                chunk = resp.read(8192)
                                if not chunk:
                                    break
                                f.write(chunk)
                                downloaded += len(chunk)
                                
                                if total > 0:
                                    pct = 50 + int(downloaded / total * 45)
                                    self.progress.emit(pct, f"Скачивание модели... {downloaded // 1024 // 1024} MB")
                    
                    # Download config
                    urllib.request.urlretrieve(config_url, config_path)
                    
                except Exception as e:
                    self.log_line.emit(f"Предупреждение: не удалось скачать модель: {e}")
                
                for model in PIPER_MODELS:
                    model.is_installed = True
                
                self.progress.emit(100, "Piper TTS установлен")
                self.operation_finished.emit(True, "Piper TTS успешно установлен")
                self.models_updated.emit(self.get_tts_models())
            else:
                self.operation_finished.emit(False, f"Ошибка pip: {result.stderr}")
                
        except Exception as e:
            self.operation_finished.emit(False, f"Ошибка установки Piper: {e}")
    
    def _install_styletts2(self):
        """Install StyleTTS2"""
        self.progress.emit(0, "Установка StyleTTS2...")
        self.log_line.emit("StyleTTS2 требует ручной установки из-за сложных зависимостей.")
        self.log_line.emit("Инструкции: https://github.com/yl4579/StyleTTS2")
        
        try:
            import subprocess
            import sys
            
            # Try to install basic dependencies
            result = subprocess.run(
                [sys.executable, "-m", "pip", "install", "styletts2"],
                capture_output=True,
                text=True,
                timeout=600
            )
            
            if result.returncode == 0:
                for model in STYLETTS2_MODELS:
                    model.is_installed = True
                
                self.progress.emit(100, "StyleTTS2 установлен")
                self.operation_finished.emit(True, "StyleTTS2 успешно установлен")
                self.models_updated.emit(self.get_tts_models())
            else:
                self.operation_finished.emit(
                    False, 
                    "StyleTTS2 требует ручной установки.\n"
                    "См. https://github.com/yl4579/StyleTTS2"
                )
        except Exception as e:
            self.operation_finished.emit(False, f"Ошибка установки StyleTTS2: {e}")
    
    def _install_bark(self):
        """Install Bark TTS"""
        self.progress.emit(0, "Установка Bark TTS...")
        self.log_line.emit("Выполняется: pip install suno-bark")
        
        try:
            import subprocess
            import sys
            
            result = subprocess.run(
                [sys.executable, "-m", "pip", "install", "suno-bark"],
                capture_output=True,
                text=True,
                timeout=600
            )
            
            if result.returncode == 0:
                self.progress.emit(100, "Bark TTS установлен")
                self.operation_finished.emit(True, "Bark TTS успешно установлен (модели скачаются при первом запуске)")
                self.models_updated.emit(self.get_tts_models())
            else:
                self.operation_finished.emit(False, f"Ошибка pip: {result.stderr}")
                
        except Exception as e:
            self.operation_finished.emit(False, f"Ошибка установки Bark: {e}")
    
    def is_tts_engine_installed(self, engine_id: str) -> bool:
        """Check if a TTS engine is installed"""
        if engine_id == "silero":
            try:
                # Check if silero model is cached (doesn't require torch import)
                cache_dir = Path.home() / ".cache" / "torch" / "hub" / "snakers4_silero-models_master"
                if cache_dir.exists():
                    return True
                # Alternative cache location
                cache_dir2 = Path.home() / ".cache" / "torch" / "hub" / "checkpoints"
                if cache_dir2.exists():
                    for f in cache_dir2.iterdir():
                        if "silero" in f.name.lower():
                            return True
                return False
            except Exception:
                return False
        
        elif engine_id == "piper":
            # Check if piper package is installed by looking for it in site-packages
            return self._is_package_installed("piper") or self._is_package_installed("piper_tts")
        
        elif engine_id == "kokoro":
            return self._is_package_installed("kokoro")
        
        elif engine_id == "styletts2":
            return self._is_package_installed("styletts2")
        
        elif engine_id == "f5tts":
            return self._is_package_installed("f5_tts") or self._is_package_installed("f5-tts")
        
        elif engine_id == "bark":
            return self._is_package_installed("bark") or self._is_package_installed("suno-bark")
        
        return False
    
    def _is_package_installed(self, package_name: str) -> bool:
        """Check if a Python package is installed without importing it"""
        import subprocess
        import sys
        
        try:
            # Use pip show which doesn't require importing the module
            result = subprocess.run(
                [sys.executable, "-m", "pip", "show", package_name],
                capture_output=True,
                text=True,
                timeout=10
            )
            return result.returncode == 0
        except Exception:
            # Fallback: check in site-packages directories
            try:
                import site
                for site_dir in site.getsitepackages() + [site.getusersitepackages()]:
                    pkg_dir = Path(site_dir) / package_name.replace("-", "_")
                    if pkg_dir.exists():
                        return True
                    # Also check for .dist-info
                    for item in Path(site_dir).glob(f"{package_name.replace('-', '_')}*"):
                        if item.is_dir():
                            return True
            except Exception:
                pass
            return False