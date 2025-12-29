"""
Voice Models Manager - STT (Vosk) and TTS (Silero) model management
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
from typing import Optional, List, Dict, Callable

from PyQt6.QtCore import QObject, QThread, pyqtSignal


class ModelType(Enum):
    """Type of voice model"""
    STT = "stt"  # Speech-to-Text (Vosk)
    TTS = "tts"  # Text-to-Speech (Silero)


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
    
    def get_stt_models(self) -> List[VoiceModel]:
        """Get all STT models"""
        return [m for m in VOSK_MODELS]
    
    def get_tts_models(self) -> List[VoiceModel]:
        """Get all TTS models"""
        return [m for m in SILERO_MODELS]
    
    def get_models_by_language(self, language: str) -> List[VoiceModel]:
        """Get models for a specific language"""
        return [m for m in VOSK_MODELS + SILERO_MODELS if m.language == language]
    
    def download_model(self, model: VoiceModel):
        """Download and install a model"""
        if model.model_type == ModelType.TTS:
            # TTS models are auto-downloaded by torch
            self._download_silero()
            return
        
        worker = DownloadWorker(model, self.models_dir)
        worker.progress.connect(self.progress.emit)
        worker.finished.connect(self._on_download_finished)
        self._workers.append(worker)
        worker.start()
    
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
            shutil.rmtree(model.local_path)
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
