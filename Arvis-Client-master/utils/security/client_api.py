"""
Client API для взаимодействия с Arvis Server
Реализует эндпоинты /api/auth/* согласно документации сервера.
"""

import json
from typing import Dict, Optional, Tuple

import requests

from utils.logger import ModuleLogger
from config.config import Config


class ArvisClientAPI:
    """
    Клиент для работы с Authentication API сервера Arvis.
    """

    _instance: Optional["ArvisClientAPI"] = None

    def __init__(self, server_url: str, timeout: int = 10):
        """
        Инициализация клиента API.

        Args:
            server_url: Базовый URL сервера (например, "http://192.168.0.107:8000").
            timeout: Таймаут запросов в секундах.
        """
        self.logger = ModuleLogger("ArvisClientAPI")
        self.server_url = server_url.rstrip("/")
        self.api_base_url = f"{self.server_url}/api/auth"
        self.timeout = timeout
        self.token: Optional[str] = None
        self.user_info: Optional[Dict] = None
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Arvis-Client/1.5.1',
            'Content-Type': 'application/json'
        })

        self.logger.info(f"Client API initialized for server: {self.server_url}")

    def _get_headers(self) -> Dict[str, str]:
        """Формирует заголовки для запроса, добавляя токен авторизации, если он есть."""
        headers: Dict[str, str] = {k: str(v) for k, v in self.session.headers.items()}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        return headers

    def _handle_response(self, response: requests.Response) -> Tuple[bool, Dict]:
        """Обрабатывает HTTP-ответ от сервера."""
        try:
            data = response.json()
        except json.JSONDecodeError:
            data = {"detail": response.text or "No content"}

        if response.ok:
            return True, data
        
        error_msg = data.get('detail', 'Unknown error')
        self.logger.error(f"API Error ({response.status_code}): {error_msg}")
        # Добавляем status_code в словарь с ошибкой для дальнейшей обработки
        if isinstance(data, dict):
            data['status_code'] = str(response.status_code)
        return False, data

    def _make_request(
        self,
        method: str,
        endpoint: str,
        data: Optional[Dict] = None,
        auth_required: bool = False,
        use_api_prefix: bool = True,
        full_url: Optional[str] = None
    ) -> Tuple[bool, Dict]:
        """
        Выполняет HTTP-запрос к серверу.

        Args:
            method: HTTP-метод ('GET', 'POST', 'PUT', 'DELETE').
            endpoint: Эндпоинт API (например, '/login').
            data: Данные для отправки в теле запроса.
            auth_required: Требуется ли токен авторизации.
            use_api_prefix: Использовать ли префикс /api/auth.
            full_url: Полный URL (если указан, игнорирует endpoint и use_api_prefix).

        Returns:
            Кортеж (успех, данные_ответа).
        """
        if full_url:
            url = full_url
        else:
            base_url = self.api_base_url if use_api_prefix else self.server_url
            url = f"{base_url}{endpoint}"
        
        headers = self._get_headers()

        if auth_required and not self.token:
            self.logger.error("Authentication required, but no token is available.")
            return False, {"detail": "Authentication token not found."}

        try:
            response = self.session.request(method, url, json=data, headers=headers, timeout=self.timeout)
            return self._handle_response(response)

        except requests.exceptions.ConnectionError as e:
            self.logger.error(f"❌ Connection error to {url}: {e}")
            return False, {"detail": "Cannot connect to the server."}
        except requests.exceptions.Timeout:
            self.logger.error(f"⏱️ Timeout error for {url} after {self.timeout}s.")
            return False, {"detail": "The server did not respond in time."}
        except Exception as e:
            self.logger.error(f"❌ An unexpected error occurred: {e}")
            return False, {"detail": str(e)}

    # ========== Информация о сервере ==========

    def check_connection(self) -> bool:
        """Проверяет соединение с сервером через /health."""
        self.logger.info("Checking connection to server...")
        success, response = self._make_request("GET", "/health", use_api_prefix=False)
        if success and response.get("status") == "healthy":
            self.logger.info(f"✓ Server is healthy (Version: {response.get('version', 'N/A')})")
            return True
        
        error = response.get("detail", "Server is not healthy or unreachable")
        self.logger.warning(f"⚠ Server connection check failed: {error}")
        return False

    # ========== Аутентификация ==========

    def login(self, username: str, password: str) -> Dict:
        """
        Вход в систему.

        Args:
            username: Имя пользователя.
            password: Пароль.

        Returns:
            Словарь с результатом. При успехе содержит токен и данные пользователя.
        """
        self.logger.info(f"Attempting to log in as '{username}'...")
        data = {"username": username, "password": password}
        success, response = self._make_request("POST", "/login", data=data)

        if success and "access_token" in response:
            self.token = response.get("access_token")
            self.user_info = response.get("user")
            self.logger.info(f"✓ Login successful for user '{username}'.")
            return {"success": True, **response}
        
        error_detail = response.get("detail", "Login failed.")
        self.logger.error(f"✗ Login failed for '{username}': {error_detail}")
        return {"success": False, "detail": error_detail}

    def register(self, username: str, password: str, email: Optional[str] = None, 
                 use_client_endpoint: bool = False) -> Dict:
        """
        Регистрация нового пользователя.

        Args:
            username: Имя пользователя (минимум 3 символа).
            password: Пароль (минимум 8 символов).
            email: Email (опционально).
            use_client_endpoint: Использовать /api/client/register вместо /api/auth/register.

        Returns:
            Словарь с результатом.
        """
        self.logger.info(f"Attempting to register new user '{username}'...")
        
        # Формируем данные запроса согласно документации
        data = {"username": username, "password": password}
        if email:
            data["email"] = email
        
        # Выбираем эндпоинт
        if use_client_endpoint:
            # Для /api/client/register используем полный URL
            url = f"{self.server_url}/api/client/register"
            self.logger.info("Using /api/client/register endpoint")
            success, response = self._make_request("POST", "", data=data, full_url=url)
        else:
            endpoint = "/register"
            self.logger.info("Using /api/auth/register endpoint")
            success, response = self._make_request("POST", endpoint, data=data)

        if success:
            # Если успешно и есть токен - сохраняем
            if "access_token" in response:
                self.token = response.get("access_token")
                self.user_info = {
                    "username": response.get("username"),
                    "email": response.get("email"),
                    "role": response.get("role"),
                    "user_id": response.get("user_id")
                }
            self.logger.info(f"✓ User '{username}' registered successfully.")
            return {"success": True, **response}
            
        error_detail = response.get("detail", "Registration failed.")
        self.logger.error(f"✗ Registration failed for '{username}': {error_detail}")
        
        # Если первый эндпоинт не сработал и мы не пробовали альтернативный - пробуем его
        if not use_client_endpoint and "404" in str(error_detail):
            self.logger.info("Trying alternative endpoint /api/client/register...")
            return self.register(username, password, email, use_client_endpoint=True)
        
        return {"success": False, "detail": error_detail}

    def get_current_user(self) -> Optional[Dict]:
        """
        Получает информацию о текущем авторизованном пользователе.

        Returns:
            Словарь с данными пользователя или None.
        """
        self.logger.info("Fetching current user info...")
        success, response = self._make_request("GET", "/me", auth_required=True)

        if success:
            self.user_info = response
            self.logger.info(f"✓ Successfully fetched info for user '{self.user_info.get('username')}'.")
            return self.user_info
        
        self.logger.warning("⚠ Could not fetch current user info.")
        # Если токен невалиден (401), сбрасываем его
        if isinstance(response, dict) and response.get("status_code") == 401:
            self.token = None
        return None

    def logout(self) -> bool:
        """
        Выход из системы.

        Returns:
            True, если выход успешен.
        """
        self.logger.info("Logging out...")
        if self.token:
            self._make_request("POST", "/logout", auth_required=True)
        
        # Сбрасываем локальные данные в любом случае
        self.token = None
        self.user_info = None
        self.logger.info("✓ Local session cleared.")
        return True

    def is_logged_in(self) -> bool:
        """Проверяет, есть ли активный токен."""
        return self.token is not None

# Singleton-like accessor
_client_instance: Optional[ArvisClientAPI] = None

def get_client_api(config: Optional[Config] = None) -> Optional[ArvisClientAPI]:
    """
    Возвращает синглтон-экземпляр ArvisClientAPI.
    """
    global _client_instance
    if _client_instance is None:
        if config is None:
            config = Config()
        
        use_remote = config.get("security.auth.use_remote_server", False)
        server_url = str(config.get("security.auth.server_url", ""))

        if use_remote and server_url:
            _client_instance = ArvisClientAPI(server_url)
        else:
            ModuleLogger("ArvisClientAPI").warning("Remote server is not configured. Client API is disabled.")
            return None
            
    return _client_instance
