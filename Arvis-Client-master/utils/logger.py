"""
Logging utilities for Arvis
"""

import logging
import os
import sys
from datetime import datetime
from logging.handlers import RotatingFileHandler, TimedRotatingFileHandler
from pathlib import Path
from typing import Optional, Union


def _ensure_dir(p: Path):
    p.mkdir(parents=True, exist_ok=True)


def _build_log_file(log_dir: Path, mode: str = "session") -> Path:
    pid = os.getpid()
    now = datetime.now()
    if mode == "daily":
        name = f"arvis_{now.strftime('%Y%m%d')}.log"
    elif mode == "hourly":
        name = f"arvis_{now.strftime('%Y%m%d_%H')}.log"
    elif mode == "single":
        name = "arvis.log"
    else:  # session (default)
        name = f"arvis_{now.strftime('%Y%m%d_%H%M%S')}_{pid}.log"
    return log_dir / name


def setup_logger(
    name: str = "Arvis",
    config: Optional[Union[dict, object]] = None,
    log_level: str = "INFO",
    log_file: Optional[Path] = None,
):
    """Setup logger with console and file handlers.

    Supports config-driven settings:
      logging.level, logging.console_level, logging.file_level,
      logging.file_logging, logging.mode (session|daily|hourly|single),
      logging.rotation (size|time|none), logging.max_bytes, logging.backup_count,
      paths.logs
    """

    # Resolve configuration values
    def cfg(key, default=None):
        if config is None:
            return default
        # config might be a Config object or dict
        if hasattr(config, "get") and callable(getattr(config, "get")):
            try:
                return config.get(key, default)
            except Exception:
                return default
        if isinstance(config, dict):
            # dotted access for dict
            cur = config
            for part in key.split("."):
                if isinstance(cur, dict) and part in cur:
                    cur = cur[part]
                else:
                    return default
            return cur
        return default

    level = cfg("logging.level", log_level).upper() if isinstance(cfg("logging.level", log_level), str) else log_level
    console_level = cfg("logging.console_level", "INFO").upper()
    file_level = cfg("logging.file_level", "DEBUG").upper()
    file_logging = bool(cfg("logging.file_logging", True))
    mode = cfg("logging.mode", "session")  # session|daily|hourly|single
    rotation = cfg("logging.rotation", "size")  # size|time|none
    max_bytes = int(cfg("logging.max_bytes", 5 * 1024 * 1024))  # 5MB
    backup_count = int(cfg("logging.backup_count", 7))
    logs_dir = Path(cfg("paths.logs", "logs"))

    # Create logger
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, level, logging.INFO))

    # Clear existing handlers
    logger.handlers.clear()

    # Formatters
    console_formatter = logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s", datefmt="%H:%M:%S")
    file_formatter = logging.Formatter("%(asctime)s %(levelname)s %(name)s [%(filename)s:%(lineno)d]: %(message)s")

    # Console handler
    console_handler = logging.StreamHandler(stream=sys.stdout)
    console_handler.setLevel(getattr(logging, console_level, logging.INFO))
    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)

    # File handler
    if file_logging:
        _ensure_dir(logs_dir)
        if log_file is None:
            log_file = _build_log_file(logs_dir, mode)

        if rotation == "none":
            fh = logging.FileHandler(log_file, encoding="utf-8")
        elif rotation == "time":
            # Timed rotation - align with mode
            when = "midnight" if mode in ("daily", "single", "session") else "H"
            fh = TimedRotatingFileHandler(
                str(log_file), when=when, interval=1, backupCount=backup_count, encoding="utf-8", utc=False
            )
        else:
            # size-based rotation
            fh = RotatingFileHandler(str(log_file), maxBytes=max_bytes, backupCount=backup_count, encoding="utf-8")

        fh.setLevel(getattr(logging, file_level, logging.DEBUG))
        fh.setFormatter(file_formatter)
        logger.addHandler(fh)

    return logger


class ModuleLogger:
    """Logger wrapper for modules"""

    def __init__(self, module_name: str):
        self.logger = logging.getLogger(f"Arvis.{module_name}")

    def info(self, message: str):
        self.logger.info(message)

    def debug(self, message: str):
        self.logger.debug(message)

    def warning(self, message: str):
        self.logger.warning(message)

    def error(self, message: str):
        self.logger.error(message)

    def critical(self, message: str):
        self.logger.critical(message)
