"""
Быстрый HTTP клиент с пулом соединений для предотвращения зависаний
"""

import threading
import time
from typing import Any, Dict, Optional

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from utils.logger import ModuleLogger


class FastHTTPClient:
    """Быстрый HTTP клиент с пулом соединений и таймаутами"""

    def __init__(self, base_url: str, timeout: float = 2.0):
        # Нормализуем базовый URL и избегаем ловушек localhost/IPv6
        normalized = base_url.rstrip("/")
        if "localhost" in normalized:
            # localhost иногда резолвится в ::1 (IPv6) и может виснуть на некоторых конфигурациях Windows
            normalized = normalized.replace("localhost", "127.0.0.1")
        self.base_url = normalized
        # Дефолтный таймаут чуть больше, чтобы избежать ложных таймаутов на загруженных системах
        self.timeout = max(timeout, 5.0)
        self.logger = ModuleLogger("FastHTTPClient")

        # Создаём сессию с пулом соединений
        self.session = requests.Session()
        # Отключаем использование системных прокси для локальных запросов
        self.session.trust_env = False

        # Настройка retry стратегии
        retry_strategy = Retry(
            total=2,  # Максимум 2 попытки
            status_forcelist=[429, 500, 502, 503, 504],
            backoff_factor=0.1,  # Быстрые повторы
            raise_on_status=False,
        )

        # HTTP адаптер с пулом соединений
        adapter = HTTPAdapter(pool_connections=5, pool_maxsize=10, max_retries=retry_strategy, pool_block=False)

        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)

        # Устанавливаем заголовки по умолчанию
        self.session.headers.update({"User-Agent": "Arvis/1.1.0", "Connection": "keep-alive"})

        # Кэш для результатов
        self._cache = {}
        self._cache_lock = threading.Lock()
        self._cache_timeout = 5.0  # 5 секунд кэша

    def _get_cache_key(self, method: str, endpoint: str) -> str:
        """Получить ключ кэша"""
        return f"{method}:{endpoint}"

    def _is_cache_valid(self, timestamp: float) -> bool:
        """Проверить валидность кэша"""
        return time.time() - timestamp < self._cache_timeout

    def _get_from_cache(self, cache_key: str) -> Optional[Dict[str, Any]]:
        """Получить из кэша"""
        with self._cache_lock:
            if cache_key in self._cache:
                result, timestamp = self._cache[cache_key]
                if self._is_cache_valid(timestamp):
                    return result
                else:
                    del self._cache[cache_key]
        return None

    def _set_cache(self, cache_key: str, result: Dict[str, Any]):
        """Сохранить в кэш"""
        with self._cache_lock:
            self._cache[cache_key] = (result, time.time())

    def get(self, endpoint: str, use_cache: bool = True) -> Dict[str, Any]:
        """Быстрый GET запрос"""
        cache_key = self._get_cache_key("GET", endpoint)

        # Проверяем кэш
        if use_cache:
            cached = self._get_from_cache(cache_key)
            if cached:
                return cached

        try:
            url = f"{self.base_url}{endpoint}"
            # Раздельные таймауты: (connect, read)
            response = self.session.get(url, timeout=(2.0, self.timeout))

            result = {
                "success": response.status_code == 200,
                "status_code": response.status_code,
                "data": response.json() if response.status_code == 200 else None,
                "error": None,
            }

            # Кэшируем успешные результаты
            if result["success"] and use_cache:
                self._set_cache(cache_key, result)

            return result

        except requests.exceptions.Timeout:
            return {"success": False, "status_code": 0, "data": None, "error": "timeout"}
        except requests.exceptions.ConnectionError:
            return {"success": False, "status_code": 0, "data": None, "error": "connection_error"}
        except Exception as e:
            return {"success": False, "status_code": 0, "data": None, "error": str(e)}

    def post(
        self, endpoint: str, data: Dict[str, Any] = None, json_data: Dict[str, Any] = None, stream: bool = False
    ) -> Dict[str, Any]:
        """Быстрый POST запрос"""
        try:
            url = f"{self.base_url}{endpoint}"

            # Раздельные таймауты: быстрый коннект и более щадящее чтение
            kwargs = {"timeout": (2.0, self.timeout if not stream else 30)}
            if data:
                kwargs["data"] = data
            if json_data:
                kwargs["json"] = json_data
            if stream:
                kwargs["stream"] = True

            response = self.session.post(url, **kwargs)

            if stream:
                return {"success": True, "status_code": response.status_code, "response": response, "error": None}
            else:
                return {
                    "success": response.status_code == 200,
                    "status_code": response.status_code,
                    "data": response.json() if response.status_code == 200 else None,
                    "error": None,
                }

        except requests.exceptions.Timeout:
            return {"success": False, "status_code": 0, "data": None, "error": "timeout"}
        except requests.exceptions.ConnectionError:
            return {"success": False, "status_code": 0, "data": None, "error": "connection_error"}
        except Exception as e:
            return {"success": False, "status_code": 0, "data": None, "error": str(e)}

    def is_alive(self) -> bool:
        """Быстрая проверка доступности сервера"""
        result = self.get("/api/tags", use_cache=True)
        return result["success"]

    def clear_cache(self):
        """Очистить кэш"""
        with self._cache_lock:
            self._cache.clear()

    def close(self):
        """Закрыть все соединения"""
        try:
            self.session.close()
        except Exception as e:
            self.logger.error(f"Error closing HTTP client: {e}")
