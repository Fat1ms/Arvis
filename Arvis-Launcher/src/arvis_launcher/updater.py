"""
Update manager for Arvis Launcher
Handles checking and downloading updates from GitHub
"""

from __future__ import annotations

import json
import os
import shutil
import tempfile
import zipfile
import urllib.request
import urllib.error
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, List, Dict, Any
from datetime import datetime

from PyQt6.QtCore import QObject, QThread, pyqtSignal


@dataclass
class ReleaseInfo:
    """Information about a GitHub release"""
    tag_name: str
    name: str
    body: str  # Changelog/description
    published_at: str
    html_url: str
    assets: List[Dict[str, Any]]
    prerelease: bool = False
    
    @property
    def version(self) -> str:
        """Get version string without 'v' prefix"""
        tag = self.tag_name
        if tag.startswith("v"):
            tag = tag[1:]
        return tag
    
    @property
    def published_date(self) -> str:
        """Get formatted publish date"""
        try:
            dt = datetime.fromisoformat(self.published_at.replace("Z", "+00:00"))
            return dt.strftime("%d.%m.%Y")
        except:
            return self.published_at
    
    def get_zip_asset(self) -> Optional[Dict[str, Any]]:
        """Get the Windows zip asset"""
        for asset in self.assets:
            name = asset.get("name", "").lower()
            if name.endswith(".zip") and ("windows" in name or "win" in name or "client" in name):
                return asset
        # Fallback: any zip
        for asset in self.assets:
            if asset.get("name", "").lower().endswith(".zip"):
                return asset
        return None


class UpdateCheckWorker(QThread):
    """Background worker for checking updates"""
    
    finished = pyqtSignal(object, str)  # ReleaseInfo or None, error message
    
    def __init__(self, repo: str, current_version: str, include_prerelease: bool = False, parent=None):
        super().__init__(parent)
        self.repo = repo
        self.current_version = current_version
        self.include_prerelease = include_prerelease
    
    def run(self):
        try:
            release = self._check_for_update()
            self.finished.emit(release, "")
        except Exception as e:
            self.finished.emit(None, str(e))
    
    def _check_for_update(self) -> Optional[ReleaseInfo]:
        """Check GitHub for new release"""
        api_url = f"https://api.github.com/repos/{self.repo}/releases"
        
        if not self.include_prerelease:
            api_url = f"https://api.github.com/repos/{self.repo}/releases/latest"
        
        req = urllib.request.Request(api_url)
        req.add_header("Accept", "application/vnd.github.v3+json")
        req.add_header("User-Agent", "Arvis-Launcher")
        
        try:
            with urllib.request.urlopen(req, timeout=15) as response:
                data = json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return None  # No releases
            raise
        
        # Handle single release (latest) vs list
        if isinstance(data, dict):
            releases = [data]
        else:
            releases = data
        
        if not releases:
            return None
        
        # Find newest suitable release
        for release_data in releases:
            if not self.include_prerelease and release_data.get("prerelease", False):
                continue
            
            release = ReleaseInfo(
                tag_name=release_data["tag_name"],
                name=release_data.get("name", release_data["tag_name"]),
                body=release_data.get("body", ""),
                published_at=release_data.get("published_at", ""),
                html_url=release_data.get("html_url", ""),
                assets=release_data.get("assets", []),
                prerelease=release_data.get("prerelease", False)
            )
            
            # Compare versions
            if self._is_newer(release.version, self.current_version):
                return release
        
        return None
    
    def _is_newer(self, remote: str, local: str) -> bool:
        """Compare version strings"""
        try:
            def parse_version(v: str) -> tuple:
                parts = v.replace("-", ".").split(".")
                result = []
                for part in parts:
                    try:
                        result.append(int(part))
                    except ValueError:
                        result.append(0)
                return tuple(result)
            
            return parse_version(remote) > parse_version(local)
        except:
            return remote != local


class UpdateDownloadWorker(QThread):
    """Background worker for downloading and installing updates"""
    
    progress = pyqtSignal(int, str)
    log_line = pyqtSignal(str)
    finished = pyqtSignal(bool, str)
    
    def __init__(self, release: ReleaseInfo, target_dir: Path, parent=None):
        super().__init__(parent)
        self.release = release
        self.target_dir = Path(target_dir)
        self._cancelled = False
    
    def cancel(self):
        self._cancelled = True
    
    def run(self):
        try:
            self._download_and_install()
        except Exception as e:
            self.finished.emit(False, f"Ошибка: {e}")
    
    def _download_and_install(self):
        """Download and extract update"""
        asset = self.release.get_zip_asset()
        if not asset:
            self.finished.emit(False, "ZIP-архив не найден в релизе")
            return
        
        download_url = asset["browser_download_url"]
        file_size = asset.get("size", 0)
        
        self.progress.emit(0, "Скачивание обновления...")
        self.log_line.emit(f"Скачивание: {asset['name']}")
        
        # Download to temp file
        try:
            with tempfile.NamedTemporaryFile(suffix=".zip", delete=False) as tmp:
                tmp_path = tmp.name
            
            def reporthook(block_num, block_size, total_size):
                if self._cancelled:
                    raise InterruptedError("Cancelled")
                if total_size > 0:
                    downloaded = block_num * block_size
                    percent = min(int(downloaded * 70 / total_size), 70)
                    mb_done = downloaded // 1024 // 1024
                    mb_total = total_size // 1024 // 1024
                    self.progress.emit(percent, f"Скачивание: {mb_done}/{mb_total} MB")
            
            urllib.request.urlretrieve(download_url, tmp_path, reporthook)
            
        except InterruptedError:
            self.finished.emit(False, "Скачивание отменено")
            return
        except Exception as e:
            self.finished.emit(False, f"Ошибка скачивания: {e}")
            return
        
        # Extract
        self.progress.emit(75, "Распаковка...")
        self.log_line.emit("Распаковка архива...")
        
        try:
            # Create backup of current installation
            backup_dir = self.target_dir.parent / f"{self.target_dir.name}_backup"
            if backup_dir.exists():
                shutil.rmtree(backup_dir, ignore_errors=True)
            
            # Extract to temp directory first
            extract_dir = Path(tempfile.mkdtemp())
            
            with zipfile.ZipFile(tmp_path, 'r') as zf:
                zf.extractall(extract_dir)
            
            # Find the actual content directory (might be nested)
            content_dir = extract_dir
            subdirs = list(extract_dir.iterdir())
            if len(subdirs) == 1 and subdirs[0].is_dir():
                # Content is in a single subdirectory
                content_dir = subdirs[0]
            
            self.progress.emit(85, "Установка файлов...")
            
            # Copy files (preserve user data)
            preserved_dirs = {"config", "data", "logs", "models", ".venv", "venv"}
            preserved_files = {"launcher_config.json"}
            
            for item in content_dir.iterdir():
                target_path = self.target_dir / item.name
                
                # Skip preserved items
                if item.name in preserved_dirs or item.name in preserved_files:
                    if target_path.exists():
                        self.log_line.emit(f"Пропуск (сохранено): {item.name}")
                        continue
                
                # Remove old and copy new
                if target_path.exists():
                    if target_path.is_dir():
                        shutil.rmtree(target_path)
                    else:
                        target_path.unlink()
                
                if item.is_dir():
                    shutil.copytree(item, target_path)
                else:
                    shutil.copy2(item, target_path)
                
                self.log_line.emit(f"Обновлено: {item.name}")
            
            # Cleanup
            shutil.rmtree(extract_dir, ignore_errors=True)
            os.unlink(tmp_path)
            
            self.progress.emit(100, "Готово!")
            self.log_line.emit(f"✓ Обновление до версии {self.release.version} завершено!")
            self.finished.emit(True, f"Обновлено до версии {self.release.version}")
            
        except Exception as e:
            self.finished.emit(False, f"Ошибка распаковки: {e}")


class UpdateManager(QObject):
    """High-level update manager"""
    
    update_available = pyqtSignal(object)    # ReleaseInfo
    no_update = pyqtSignal()
    check_error = pyqtSignal(str)
    
    progress = pyqtSignal(int, str)
    log_line = pyqtSignal(str)
    update_finished = pyqtSignal(bool, str)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._check_worker = None
        self._download_worker = None
        self._latest_release: Optional[ReleaseInfo] = None
    
    @property
    def latest_release(self) -> Optional[ReleaseInfo]:
        return self._latest_release
    
    def check_for_updates(self, repo: str, current_version: str, include_dev: bool = False):
        """Check for updates from GitHub"""
        if self._check_worker and self._check_worker.isRunning():
            return
        
        self._check_worker = UpdateCheckWorker(repo, current_version, include_dev)
        self._check_worker.finished.connect(self._on_check_finished)
        self._check_worker.start()
    
    def _on_check_finished(self, release: Optional[ReleaseInfo], error: str):
        """Handle check completion"""
        self._check_worker = None
        
        if error:
            self.check_error.emit(error)
            return
        
        if release:
            self._latest_release = release
            self.update_available.emit(release)
        else:
            self.no_update.emit()
    
    def download_update(self, target_dir: Path):
        """Download and install the latest release"""
        if not self._latest_release:
            self.update_finished.emit(False, "Нет доступных обновлений")
            return
        
        if self._download_worker and self._download_worker.isRunning():
            return
        
        self._download_worker = UpdateDownloadWorker(self._latest_release, target_dir)
        self._download_worker.progress.connect(self.progress.emit)
        self._download_worker.log_line.connect(self.log_line.emit)
        self._download_worker.finished.connect(self._on_download_finished)
        self._download_worker.start()
    
    def _on_download_finished(self, success: bool, message: str):
        """Handle download completion"""
        self._download_worker = None
        self.update_finished.emit(success, message)
    
    def cancel(self):
        """Cancel current operation"""
        if self._download_worker:
            self._download_worker.cancel()


def get_local_version(client_root: Path) -> str:
    """Get version from local installation"""
    version_file = client_root / "version.py"
    if not version_file.exists():
        return "0.0.0"
    
    try:
        content = version_file.read_text(encoding="utf-8")
        # Parse VERSION = "x.y.z"
        for line in content.splitlines():
            if line.strip().startswith("VERSION"):
                # Extract string value
                if '"' in line:
                    return line.split('"')[1]
                elif "'" in line:
                    return line.split("'")[1]
        return "0.0.0"
    except:
        return "0.0.0"
