"""
Version Manager - Система управления версиями и совместимостью
Автоматически синхронизирует версии между клиентом и сервером
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional, Tuple

logger = logging.getLogger(__name__)


class VersionManager:
    """Менеджер версий для обеспечения совместимости"""

    # Минимальные требуемые версии для совместимости
    MIN_CLIENT_VERSION = "1.5.0"
    MIN_SERVER_VERSION = "1.0.0"
    
    # Файл с информацией о версиях
    VERSION_FILE = Path("data/version_info.json")
    
    def __init__(self):
        self.VERSION_FILE.parent.mkdir(parents=True, exist_ok=True)
        self._load_version_info()
    
    def _load_version_info(self):
        """Загрузить информацию о версиях"""
        if self.VERSION_FILE.exists():
            try:
                with open(self.VERSION_FILE, 'r', encoding='utf-8') as f:
                    self.version_info = json.load(f)
            except Exception as e:
                logger.warning(f"Failed to load version info: {e}")
                self.version_info = self._create_default_version_info()
        else:
            self.version_info = self._create_default_version_info()
            self._save_version_info()
    
    def _save_version_info(self):
        """Сохранить информацию о версиях"""
        try:
            with open(self.VERSION_FILE, 'w', encoding='utf-8') as f:
                json.dump(self.version_info, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"Failed to save version info: {e}")
    
    def _create_default_version_info(self) -> Dict:
        """Создать информацию о версиях по умолчанию"""
        from version import __version__
        return {
            "client_version": __version__,
            "server_version": "auto",  # Будет определена автоматически
            "last_check": datetime.now().isoformat(),
            "compatibility_mode": "auto",  # auto, strict, legacy
            "sync_enabled": True,
        }
    
    def get_client_version(self) -> str:
        """Получить версию клиента"""
        from version import __version__
        return __version__
    
    def get_server_version(self) -> Optional[str]:
        """Получить версию сервера из конфига или автоопределение"""
        return self.version_info.get("server_version", "auto")
    
    def check_compatibility(self, server_version: str) -> Tuple[bool, str]:
        """
        Проверить совместимость версий клиента и сервера
        
        Returns:
            Tuple[bool, str]: (is_compatible, message)
        """
        client_version = self.get_client_version()
        
        # Сравнение версий
        try:
            client_parts = [int(x) for x in client_version.split('.')]
            server_parts = [int(x) for x in server_version.split('.')]
            min_client_parts = [int(x) for x in self.MIN_CLIENT_VERSION.split('.')]
            min_server_parts = [int(x) for x in self.MIN_SERVER_VERSION.split('.')]
            
            # Проверка минимальных версий
            if client_parts < min_client_parts:
                return False, f"Клиент устарел. Требуется версия {self.MIN_CLIENT_VERSION} или выше"
            
            if server_parts < min_server_parts:
                return False, f"Сервер устарел. Требуется версия {self.MIN_SERVER_VERSION} или выше"
            
            # Проверка мажорных версий (должны совпадать)
            if client_parts[0] != server_parts[0]:
                return False, f"Несовместимые мажорные версии: клиент {client_version}, сервер {server_version}"
            
            return True, "Версии совместимы"
            
        except Exception as e:
            logger.error(f"Error checking compatibility: {e}")
            return True, "Проверка совместимости пропущена (авто-режим)"
    
    def update_server_version(self, server_version: str):
        """Обновить информацию о версии сервера"""
        self.version_info["server_version"] = server_version
        self.version_info["last_check"] = datetime.now().isoformat()
        self._save_version_info()
        logger.info(f"Updated server version to {server_version}")
    
    def set_compatibility_mode(self, mode: str):
        """
        Установить режим совместимости
        
        Args:
            mode: 'auto' (авто), 'strict' (строгий), 'legacy' (совместимость)
        """
        if mode not in ['auto', 'strict', 'legacy']:
            raise ValueError(f"Invalid compatibility mode: {mode}")
        
        self.version_info["compatibility_mode"] = mode
        self._save_version_info()
        logger.info(f"Compatibility mode set to {mode}")
    
    def enable_sync(self, enabled: bool = True):
        """Включить/выключить синхронизацию версий"""
        self.version_info["sync_enabled"] = enabled
        self._save_version_info()
        logger.info(f"Version sync {'enabled' if enabled else 'disabled'}")
    
    def get_version_info(self) -> Dict:
        """Получить всю информацию о версиях"""
        info = self.version_info.copy()
        info["current_client_version"] = self.get_client_version()
        return info


# Глобальный экземпляр менеджера версий
version_manager = VersionManager()


def get_version_manager() -> VersionManager:
    """Получить глобальный менеджер версий"""
    return version_manager
