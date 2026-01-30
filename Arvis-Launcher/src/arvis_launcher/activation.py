"""
Activation Key Validation Module
Модуль валидации ключей активации Arvis
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Tuple
import urllib.request
import urllib.error

logger = logging.getLogger("arvis_launcher")


class ActivationManager:
    """Управление активацией Arvis"""
    
    # Типы ключей и их описания
    KEY_TYPES = {
        "BETA": {"name": "Beta", "description": "Бета-тестирование"},
        "MNTH": {"name": "Monthly", "description": "Месячная подписка"},
        "PERM": {"name": "Permanent", "description": "Постоянная лицензия"},
        "TRIAL": {"name": "Trial", "description": "Пробный период"},
    }
    
    def __init__(self, config_dir: Path, server_url: Optional[str] = None, offline_grace_days: int = 7):
        """
        Initialize activation manager
        
        Args:
            config_dir: Directory to store activation data
            server_url: Activation server URL
            offline_grace_days: Days allowed without online validation
        """
        self.config_dir = Path(config_dir)
        self.server_url = server_url or "http://localhost:8080"
        self.activation_file = self.config_dir / "activation.json"
        self.offline_grace_days = offline_grace_days
        
    def load_activation(self) -> dict:
        """Загрузить данные активации из файла"""
        if self.activation_file.exists():
            try:
                with open(self.activation_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Failed to load activation data: {e}")
        return {}
    
    def save_activation(self, data: dict) -> bool:
        """
        Сохранить данные активации в файл
        
        Args:
            data: Activation data dictionary
            
        Returns:
            True if saved successfully
        """
        try:
            self.config_dir.mkdir(parents=True, exist_ok=True)
            with open(self.activation_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, default=str, ensure_ascii=False)
            return True
        except Exception as e:
            logger.error(f"Failed to save activation data: {e}")
            return False
    
    def validate_key_online(self, key: str, email: Optional[str] = None) -> Tuple[Optional[bool], dict]:
        """
        Проверить ключ через сервер активации
        
        Args:
            key: Activation key
            email: Optional user email
            
        Returns:
            (is_valid, response_data) - is_valid is None if server unavailable
        """
        try:
            url = f"{self.server_url}/api/keys/validate"
            payload = json.dumps({
                "key": key,
                "user_email": email
            }).encode("utf-8")
            
            req = urllib.request.Request(
                url,
                data=payload,
                headers={
                    "Content-Type": "application/json",
                    "User-Agent": "Arvis-Launcher/1.0"
                }
            )
            
            with urllib.request.urlopen(req, timeout=10) as response:
                data = json.loads(response.read().decode("utf-8"))
                return data.get("valid", False), data
                
        except urllib.error.HTTPError as e:
            logger.warning(f"Server validation failed (HTTP {e.code}): {e}")
            try:
                error_data = json.loads(e.read().decode("utf-8"))
                return False, error_data
            except Exception:
                return False, {"error": f"Ошибка сервера: {e.code}"}
        except urllib.error.URLError as e:
            logger.warning(f"Server validation failed (network error): {e}")
            return None, {"error": "Сервер недоступен", "error_code": "NETWORK_ERROR"}
        except Exception as e:
            logger.error(f"Validation error: {e}")
            return None, {"error": str(e)}
    
    def validate_key_format(self, key: str) -> Tuple[bool, str, Optional[str]]:
        """
        Офлайн-валидация формата ключа
        
        Args:
            key: Activation key to validate
            
        Returns:
            (is_valid, error_message, key_type)
        """
        if not key:
            return False, "Ключ не может быть пустым", None
            
        if len(key) < 15:
            return False, "Неверный формат ключа", None
        
        key = key.upper().strip()
        
        if not key.startswith("ARVIS-"):
            return False, "Ключ должен начинаться с ARVIS-", None
        
        parts = key.split("-")
        if len(parts) < 3:
            return False, "Неверная структура ключа", None
        
        key_type = parts[1]
        if key_type not in self.KEY_TYPES:
            return False, f"Неизвестный тип ключа: {key_type}", None
        
        # Проверка срока действия месячного ключа (офлайн)
        if key_type == "MNTH" and len(parts) >= 4:
            try:
                date_part = parts[3]
                if len(date_part) == 4:
                    year = 2000 + int(date_part[:2])
                    month = int(date_part[2:])
                    
                    now = datetime.now()
                    if year < now.year or (year == now.year and month < now.month):
                        return False, "Месячный ключ истёк", key_type
            except ValueError:
                pass  # Не удалось распарсить дату - проверим на сервере
        
        return True, "", key_type
    
    def check_activation(self, key: Optional[str] = None, email: Optional[str] = None) -> Tuple[bool, str]:
        """
        Проверить состояние активации
        
        Args:
            key: New key to activate (optional)
            email: User email (optional)
            
        Returns:
            (is_activated, message)
        """
        activation = self.load_activation()
        
        # Если передан новый ключ - активировать его
        if key:
            return self.activate(key, email)
        
        # Проверить сохранённую активацию
        saved_key = activation.get("key")
        if not saved_key:
            return False, "Требуется активация"
        
        # Офлайн проверка формата
        format_valid, format_error, key_type = self.validate_key_format(saved_key)
        if not format_valid:
            return False, format_error
        
        # Проверка истечения срока (локально)
        expires_at = activation.get("expires_at")
        if expires_at:
            try:
                # Handle both ISO format with and without timezone
                expires_str = expires_at.replace("Z", "+00:00")
                if "+" not in expires_str and "-" not in expires_str[10:]:
                    expires = datetime.fromisoformat(expires_str)
                else:
                    expires = datetime.fromisoformat(expires_str).replace(tzinfo=None)
                
                if datetime.now() > expires:
                    return False, "Срок активации истёк"
            except Exception as e:
                logger.warning(f"Failed to parse expires_at: {e}")
        
        # Онлайн проверка (с grace period для офлайна)
        last_check = activation.get("last_online_check")
        need_online_check = True
        
        if last_check:
            try:
                last_check_dt = datetime.fromisoformat(last_check)
                grace_end = last_check_dt + timedelta(days=self.offline_grace_days)
                need_online_check = datetime.now() > grace_end
            except Exception:
                pass
        
        if need_online_check:
            online_valid, response = self.validate_key_online(
                saved_key, 
                activation.get("email")
            )
            
            if online_valid is None:
                # Сервер недоступен
                if not last_check:
                    return False, "Требуется интернет-соединение для первой проверки"
                # Разрешаем офлайн-режим в пределах grace period
                logger.info("Server unavailable, using offline grace period")
            elif not online_valid:
                # Ключ больше не валиден
                error_msg = response.get("error", "Ключ недействителен")
                return False, error_msg
            else:
                # Обновить данные активации
                activation["last_online_check"] = datetime.now().isoformat()
                activation["expires_at"] = response.get("expires_at")
                activation["key_type"] = response.get("key_type", key_type)
                self.save_activation(activation)
        
        return True, "Активировано"
    
    def activate(self, key: str, email: Optional[str] = None) -> Tuple[bool, str]:
        """
        Активировать с новым ключом
        
        Args:
            key: Activation key
            email: Optional user email
            
        Returns:
            (success, message)
        """
        # Нормализация ключа
        key = key.upper().strip()
        
        # Офлайн проверка формата
        format_valid, format_error, key_type = self.validate_key_format(key)
        if not format_valid:
            return False, format_error
        
        # Онлайн валидация
        online_valid, response = self.validate_key_online(key, email)
        
        if online_valid is None:
            # Сервер недоступен - сохраняем для проверки позже
            logger.warning("Server unavailable, saving key for later validation")
            activation = {
                "key": key,
                "email": email,
                "key_type": key_type,
                "activated_at": datetime.now().isoformat(),
                "last_online_check": None,
                "expires_at": None,
                "offline_activation": True
            }
            self.save_activation(activation)
            return True, "Активировано (офлайн режим, проверка при подключении)"
        
        if not online_valid:
            error_msg = response.get("error", "Недействительный ключ")
            return False, error_msg
        
        # Сохранить успешную активацию
        activation = {
            "key": key,
            "email": email,
            "key_type": response.get("key_type", key_type),
            "activated_at": datetime.now().isoformat(),
            "last_online_check": datetime.now().isoformat(),
            "expires_at": response.get("expires_at"),
            "offline_activation": False
        }
        self.save_activation(activation)
        
        # Формируем сообщение об успешной активации
        type_info = self.KEY_TYPES.get(response.get("key_type", "").upper(), {})
        type_name = type_info.get("name", response.get("key_type", ""))
        
        return True, f"Успешно активировано ({type_name})"
    
    def deactivate(self) -> Tuple[bool, str]:
        """
        Деактивировать (удалить активацию)
        
        Returns:
            (success, message)
        """
        try:
            if self.activation_file.exists():
                self.activation_file.unlink()
            return True, "Деактивировано"
        except Exception as e:
            logger.error(f"Failed to deactivate: {e}")
            return False, f"Ошибка деактивации: {e}"
    
    def get_status(self) -> dict:
        """
        Получить подробный статус активации
        
        Returns:
            Dictionary with activation status details
        """
        activation = self.load_activation()
        
        if not activation:
            return {
                "activated": False,
                "message": "Не активировано",
                "key_type": None,
                "key_type_name": None,
                "activated_at": None,
                "expires_at": None,
                "key_preview": None,
                "email": None,
                "offline_mode": False,
                "days_remaining": None
            }
        
        is_valid, message = self.check_activation()
        
        key_type = activation.get("key_type", "").upper()
        type_info = self.KEY_TYPES.get(key_type, {})
        
        # Рассчитать оставшиеся дни
        days_remaining = None
        expires_at = activation.get("expires_at")
        if expires_at:
            try:
                expires_str = expires_at.replace("Z", "+00:00")
                if "+" not in expires_str and "-" not in expires_str[10:]:
                    expires = datetime.fromisoformat(expires_str)
                else:
                    expires = datetime.fromisoformat(expires_str).replace(tzinfo=None)
                
                delta = expires - datetime.now()
                days_remaining = max(0, delta.days)
            except Exception:
                pass
        
        # Скрыть часть ключа
        key = activation.get("key", "")
        key_preview = None
        if key:
            if len(key) > 20:
                key_preview = key[:20] + "..."
            else:
                key_preview = key
        
        return {
            "activated": is_valid,
            "message": message,
            "key_type": key_type.lower() if key_type else None,
            "key_type_name": type_info.get("name"),
            "key_type_description": type_info.get("description"),
            "activated_at": activation.get("activated_at"),
            "expires_at": expires_at,
            "key_preview": key_preview,
            "email": activation.get("email"),
            "offline_mode": activation.get("offline_activation", False),
            "days_remaining": days_remaining,
            "last_check": activation.get("last_online_check")
        }
    
    def get_key_info(self, key: str) -> Tuple[bool, dict]:
        """
        Получить информацию о ключе с сервера
        
        Args:
            key: Activation key
            
        Returns:
            (success, info_dict)
        """
        try:
            url = f"{self.server_url}/api/keys/info/{key}"
            
            req = urllib.request.Request(
                url,
                headers={"User-Agent": "Arvis-Launcher/1.0"}
            )
            
            with urllib.request.urlopen(req, timeout=10) as response:
                data = json.loads(response.read().decode("utf-8"))
                return True, data
                
        except Exception as e:
            logger.error(f"Failed to get key info: {e}")
            return False, {"error": str(e)}


# Для тестирования
if __name__ == "__main__":
    import sys
    
    manager = ActivationManager(
        config_dir=Path("./config"),
        server_url="http://localhost:8080"
    )
    
    # Проверить статус
    status = manager.get_status()
    print("Current status:", json.dumps(status, indent=2, default=str, ensure_ascii=False))
    
    # Пример активации
    if len(sys.argv) > 1:
        test_key = sys.argv[1]
        email = sys.argv[2] if len(sys.argv) > 2 else None
        
        success, msg = manager.activate(test_key, email)
        print(f"Activation: {success} - {msg}")
