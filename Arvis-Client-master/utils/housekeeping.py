"""
Домашние задачи: очистка логов, временных файлов и ограничение размеров хранения.
"""

import time
from pathlib import Path
from typing import Optional

from utils.logger import ModuleLogger


class Housekeeping:
    def __init__(self, logs_dir: str = "logs", temp_dir: str = "temp"):
        self.logs_dir = Path(logs_dir)
        self.temp_dir = Path(temp_dir)
        self.logger = ModuleLogger("Housekeeping")

    def clear_old_logs(self, days: int = 14, keep: int = 10) -> int:
        """Удаляет лог-файлы старше days, сохраняя не менее keep последних по времени.
        Возвращает количество удалённых файлов."""
        removed = 0
        try:
            if not self.logs_dir.exists():
                return 0
            files = sorted(
                [p for p in self.logs_dir.glob("*.log") if p.is_file()], key=lambda p: p.stat().st_mtime, reverse=True
            )
            now = time.time()
            for idx, p in enumerate(files):
                if idx < keep:
                    continue
                age_days = (now - p.stat().st_mtime) / 86400
                if age_days > days:
                    try:
                        p.unlink(missing_ok=True)  # type: ignore[arg-type]
                        removed += 1
                    except Exception as e:
                        self.logger.warning(f"Failed to remove old log {p.name}: {e}")
        except Exception as e:
            self.logger.error(f"Housekeeping error: {e}")
        return removed

    def trim_temp(self, max_files: int = 500, max_total_mb: int = 512) -> None:
        """Ограничивает число и общий размер файлов в TEMP."""
        try:
            if not self.temp_dir.exists():
                return
            files = [p for p in self.temp_dir.rglob("*") if p.is_file()]
            files.sort(key=lambda p: p.stat().st_mtime, reverse=True)
            # Ограничение по количеству
            for p in files[max_files:]:
                try:
                    p.unlink(missing_ok=True)  # type: ignore[arg-type]
                except Exception:
                    pass
            # Ограничение по размеру
            files = [p for p in self.temp_dir.rglob("*") if p.is_file()]
            total = sum(p.stat().st_size for p in files)
            limit = max_total_mb * 1024 * 1024
            if total > limit:
                # Удаляем самые старые, пока не войдём в лимит
                files.sort(key=lambda p: p.stat().st_mtime, reverse=True)
                while total > limit and files:
                    victim = files.pop()  # самый старый
                    try:
                        sz = victim.stat().st_size
                        victim.unlink(missing_ok=True)  # type: ignore[arg-type]
                        total -= sz
                    except Exception:
                        pass
        except Exception as e:
            self.logger.error(f"Trim temp error: {e}")


def run_periodic_housekeeping(config) -> None:
    """Запускает лёгкие задачи очистки согласно путям из конфигурации."""
    try:
        logs = str(getattr(config, "get")("paths.logs", "logs")) if hasattr(config, "get") else "logs"
        temp = str(getattr(config, "get")("paths.temp", "temp")) if hasattr(config, "get") else "temp"
        hk = Housekeeping(logs, temp)
        removed = hk.clear_old_logs(days=14, keep=10)
        if removed:
            ModuleLogger("Housekeeping").info(f"Удалено старых логов: {removed}")
        hk.trim_temp(max_files=500, max_total_mb=512)
    except Exception:
        pass
