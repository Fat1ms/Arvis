"""
Auto-Update System for Arvis
Система автоматического обновления для Arvis
"""

import hashlib
import os
import json
import logging
import shutil
import tempfile
import zipfile
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional, Tuple

import requests

from version import __version__

logger = logging.getLogger(__name__)


class UpdateChecker:
    """Проверка и установка обновлений из GitHub Releases"""

    def __init__(self, github_repo: str = "Fat1ms/Arvis-Client"):
        # Источник репозитория можно переопределить через ENV или конфиг
        # ENV: ARVIS_GITHUB_REPO
        # Конфиг: config.json → updates.github_repo (если есть)
        env_repo = os.environ.get("ARVIS_GITHUB_REPO")
        if env_repo:
            github_repo = env_repo

        # Пытаемся загрузить из конфигурации (мягко, без жёсткой зависимости)
        try:
            from config.config import Config  # type: ignore

            cfg = Config()
            repo_from_cfg = cfg.get("updates.github_repo", None)
            if isinstance(repo_from_cfg, str) and repo_from_cfg.strip():
                github_repo = repo_from_cfg.strip()
        except Exception:
            pass

        self.github_repo = github_repo
        self.current_version = __version__
        self.github_api_url = f"https://api.github.com/repos/{github_repo}/releases/latest"
        self.backup_dir = Path("backups")
        self.backup_dir.mkdir(exist_ok=True)
        self._http_headers = {
            "User-Agent": f"ArvisLauncher/{self.current_version} (+https://github.com/{github_repo})",
            "Accept": "application/vnd.github+json",
        }

    def check_for_updates(self) -> Optional[Dict]:
        """
        Проверка наличия новой версии на GitHub
        
        Returns:
            Dict с информацией об обновлении или None если обновлений нет
        """
        try:
            logger.info(f"Проверка обновлений для версии {self.current_version}...")
            response = requests.get(self.github_api_url, headers=self._http_headers, timeout=10)
            if response.status_code == 404:
                # Fallback: список релизов и выбор последнего стабильного
                fallback_url = f"https://api.github.com/repos/{self.github_repo}/releases"
                logger.info("releases/latest вернул 404 — пробуем /releases")
                response = requests.get(fallback_url, headers=self._http_headers, timeout=10)
            response.raise_for_status()

            data = response.json()
            # Если fallback вернул список — выбираем самый свежий не-драфтовый и не-пререлиз
            if isinstance(data, list):
                release_data = next(
                    (r for r in data if not r.get("draft") and not r.get("prerelease")),
                    data[0] if data else None,
                )
                if release_data is None:
                    logger.warning("Список релизов пуст — обновлений нет")
                    return None
            else:
                release_data = data
            latest_version = release_data.get("tag_name", "").lstrip("v")

            if not latest_version:
                logger.warning("Не удалось получить версию из релиза")
                return None

            logger.info(f"Последняя версия на GitHub: {latest_version}")

            if self._is_newer_version(latest_version, self.current_version):
                return {
                    "version": latest_version,
                    "name": release_data.get("name", ""),
                    "body": release_data.get("body", ""),
                    "published_at": release_data.get("published_at", ""),
                    "html_url": release_data.get("html_url", ""),
                    "assets": release_data.get("assets", []),
                }
            else:
                logger.info("Установлена последняя версия")
                return None

        except requests.RequestException as e:
            logger.error(f"Ошибка при проверке обновлений: {e}")
            return None
        except Exception as e:
            logger.error(f"Неожиданная ошибка при проверке обновлений: {e}")
            return None

    def _is_newer_version(self, remote: str, local: str) -> bool:
        """
        Сравнение версий (semantic versioning)
        
        Args:
            remote: Удалённая версия
            local: Локальная версия
            
        Returns:
            True если remote новее local
        """
        try:
            remote_parts = [int(x) for x in remote.split(".")]
            local_parts = [int(x) for x in local.split(".")]

            # Дополняем нулями до одинаковой длины
            while len(remote_parts) < len(local_parts):
                remote_parts.append(0)
            while len(local_parts) < len(remote_parts):
                local_parts.append(0)

            return remote_parts > local_parts
        except ValueError:
            # Некорректный semver (например, теги без чисел). Считаем новее, если тег отличается от локальной версии.
            logger.warning(f"Некорректный тег версии на релизе: '{remote}'. Использую строковое сравнение с локальной '{local}'.")
            return bool(remote) and remote.strip() != str(local).strip()

    def download_update(self, release_info: Dict, progress_callback=None) -> Optional[Path]:
        """
        Скачивание обновления
        
        Args:
            release_info: Информация о релизе
            progress_callback: Функция для отслеживания прогресса (получает процент)
            
        Returns:
            Path к скачанному файлу или None при ошибке
        """
        try:
            # Ищем архив с обновлением (предполагается формат: Arvis-v*.zip)
            assets = release_info.get("assets", [])
            update_asset = None

            # Предпочитаем Windows zip, затем любой zip
            preferred_order = [
                lambda a: a.get("name", "").lower() == "arvisclient-windows.zip",
                lambda a: a.get("name", "").lower().endswith(".zip") and "windows" in a.get("name", "").lower(),
                lambda a: a.get("name", "").lower().endswith(".zip") and "arvis" in a.get("name", "").lower(),
                lambda a: a.get("name", "").lower().endswith(".zip"),
            ]

            for predicate in preferred_order:
                candidate = next((a for a in assets if predicate(a)), None)
                if candidate:
                    update_asset = candidate
                    break

            if not update_asset:
                logger.error("Не найден архив обновления в релизе")
                return None

            download_url = update_asset.get("browser_download_url")
            if not download_url:
                logger.error("URL скачивания не найден")
                return None

            logger.info(f"Скачивание обновления: {update_asset['name']}")

            # Скачиваем во временную директорию
            temp_dir = Path(tempfile.gettempdir()) / "arvis_update"
            temp_dir.mkdir(exist_ok=True)
            download_path = temp_dir / update_asset["name"]

            response = requests.get(download_url, headers=self._http_headers, stream=True, timeout=30)
            response.raise_for_status()

            total_size = int(response.headers.get("content-length", 0))
            downloaded = 0

            with open(download_path, "wb") as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)

                        if progress_callback and total_size > 0:
                            progress = int((downloaded / total_size) * 100)
                            progress_callback(progress)

            logger.info(f"Обновление скачано: {download_path}")

            # Проверка контрольной суммы (если доступна)
            checksum_asset = next(
                (a for a in assets if "checksum" in a.get("name", "").lower() or "sha256" in a.get("name", "").lower()),
                None,
            )

            if checksum_asset:
                if not self._verify_checksum(download_path, checksum_asset):
                    logger.error("Контрольная сумма не совпадает!")
                    download_path.unlink()
                    return None

            return download_path

        except requests.RequestException as e:
            logger.error(f"Ошибка скачивания: {e}")
            return None
        except Exception as e:
            logger.error(f"Неожиданная ошибка при скачивании: {e}")
            return None

    def _verify_checksum(self, file_path: Path, checksum_asset: Dict) -> bool:
        """Проверка контрольной суммы файла"""
        try:
            # Скачиваем файл с контрольной суммой
            checksum_url = checksum_asset.get("browser_download_url")
            if not checksum_url:
                return True  # Если нет URL, пропускаем проверку

            response = requests.get(checksum_url, headers=self._http_headers, timeout=10)
            response.raise_for_status()
            expected_hash = response.text.strip().split()[0]

            # Вычисляем SHA256
            sha256 = hashlib.sha256()
            with open(file_path, "rb") as f:
                for chunk in iter(lambda: f.read(8192), b""):
                    sha256.update(chunk)

            actual_hash = sha256.hexdigest()
            return actual_hash.lower() == expected_hash.lower()

        except Exception as e:
            logger.warning(f"Не удалось проверить контрольную сумму: {e}")
            return True  # При ошибке разрешаем продолжить

    def create_backup(self) -> Optional[Path]:
        """
        Создание резервной копии текущей версии
        
        Returns:
            Path к резервной копии или None при ошибке
        """
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_name = f"arvis_backup_v{self.current_version}_{timestamp}.zip"
            backup_path = self.backup_dir / backup_name

            logger.info(f"Создание резервной копии: {backup_path}")

            # Директории для бэкапа
            backup_items = [
                "src",
                "modules",
                "utils",
                "config",
                "i18n",
                "UXUI",
                "main.py",
                "version.py",
                "requirements.txt",
            ]

            with zipfile.ZipFile(backup_path, "w", zipfile.ZIP_DEFLATED) as zipf:
                for item_name in backup_items:
                    item_path = Path(item_name)
                    if not item_path.exists():
                        continue

                    if item_path.is_file():
                        zipf.write(item_path, item_path.name)
                    elif item_path.is_dir():
                        for file_path in item_path.rglob("*"):
                            if file_path.is_file():
                                arcname = file_path.relative_to(Path.cwd())
                                zipf.write(file_path, arcname)

            logger.info(f"Резервная копия создана: {backup_path} ({backup_path.stat().st_size / (1024*1024):.2f} МБ)")
            return backup_path

        except Exception as e:
            logger.error(f"Ошибка создания резервной копии: {e}")
            return None

    def apply_update(self, update_archive: Path) -> bool:
        """
        Применение обновления
        
        Args:
            update_archive: Path к скачанному архиву
            
        Returns:
            True при успешном обновлении
        """
        try:
            logger.info("Начало установки обновления...")

            # Создаём резервную копию
            backup = self.create_backup()
            if not backup:
                logger.error("Не удалось создать резервную копию")
                return False

            # Временная директория для распаковки
            temp_extract = Path(tempfile.gettempdir()) / "arvis_extract"
            if temp_extract.exists():
                shutil.rmtree(temp_extract)
            temp_extract.mkdir()

            # Распаковываем архив
            logger.info("Распаковка обновления...")
            with zipfile.ZipFile(update_archive, "r") as zipf:
                zipf.extractall(temp_extract)

            # Находим корневую директорию (часто архивы содержат вложенную папку)
            extracted_items = list(temp_extract.iterdir())
            if len(extracted_items) == 1 and extracted_items[0].is_dir():
                source_dir = extracted_items[0]
            else:
                source_dir = temp_extract

            # Применяем обновления
            logger.info("Копирование файлов обновления...")
            update_items = [
                "src",
                "modules",
                "utils",
                "config",
                "i18n",
                "UXUI",
                "main.py",
                "version.py",
                "requirements.txt",
            ]

            for item_name in update_items:
                source_item = source_dir / item_name
                if not source_item.exists():
                    continue

                dest_item = Path(item_name)

                # Удаляем старый файл/директорию
                if dest_item.exists():
                    if dest_item.is_file():
                        dest_item.unlink()
                    elif dest_item.is_dir():
                        shutil.rmtree(dest_item)

                # Копируем новый
                if source_item.is_file():
                    shutil.copy2(source_item, dest_item)
                elif source_item.is_dir():
                    shutil.copytree(source_item, dest_item)

            # Очистка временных файлов
            shutil.rmtree(temp_extract)
            update_archive.unlink()

            logger.info("✓ Обновление успешно установлено!")
            logger.info(f"Резервная копия сохранена: {backup}")

            # Записываем информацию об обновлении
            self._save_update_info(backup)

            return True

        except Exception as e:
            logger.error(f"Ошибка применения обновления: {e}")
            logger.error("Попытка восстановления из резервной копии...")

            if backup and backup.exists():
                self.rollback_update(backup)

            return False

    def rollback_update(self, backup_path: Path) -> bool:
        """
        Откат к резервной копии
        
        Args:
            backup_path: Path к резервной копии
            
        Returns:
            True при успешном откате
        """
        try:
            logger.info(f"Откат к резервной копии: {backup_path}")

            with zipfile.ZipFile(backup_path, "r") as zipf:
                zipf.extractall(Path.cwd())

            logger.info("✓ Откат выполнен успешно")
            return True

        except Exception as e:
            logger.error(f"Ошибка отката: {e}")
            return False

    def _save_update_info(self, backup_path: Path):
        """Сохранение информации об обновлении"""
        try:
            info_file = Path("data/last_update.json")
            info_file.parent.mkdir(exist_ok=True)

            info = {
                "timestamp": datetime.now().isoformat(),
                "from_version": self.current_version,
                "backup_path": str(backup_path),
            }

            with open(info_file, "w", encoding="utf-8") as f:
                json.dump(info, f, indent=2, ensure_ascii=False)

        except Exception as e:
            logger.warning(f"Не удалось сохранить информацию об обновлении: {e}")

    def cleanup_old_backups(self, keep_count: int = 3):
        """
        Удаление старых резервных копий
        
        Args:
            keep_count: Количество последних копий для сохранения
        """
        try:
            backups = sorted(self.backup_dir.glob("arvis_backup_*.zip"), key=lambda p: p.stat().st_mtime, reverse=True)

            if len(backups) > keep_count:
                for old_backup in backups[keep_count:]:
                    logger.info(f"Удаление старой резервной копии: {old_backup.name}")
                    old_backup.unlink()

        except Exception as e:
            logger.warning(f"Ошибка очистки старых копий: {e}")
