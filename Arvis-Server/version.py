"""
Server Version Information
Информация о версии сервера
"""

__server_version__ = "1.5.1"
__server_name__ = "Arvis Auth Server"

# API версии для обратной совместимости
API_VERSION = "v1"
API_MIN_CLIENT_VERSION = "1.5.0"


def get_server_version() -> str:
    """Получить версию сервера"""
    return __server_version__


def get_server_name() -> str:
    """Получить название сервера"""
    return __server_name__


def get_full_server_info() -> dict:
    """Получить полную информацию о сервере"""
    return {
        "name": __server_name__,
        "version": __server_version__,
        "api_version": API_VERSION,
        "min_client_version": API_MIN_CLIENT_VERSION,
    }


def check_client_compatibility(client_version: str) -> tuple[bool, str]:
    """
    Проверить совместимость версии клиента
    
    Args:
        client_version: Версия клиента (например, "1.5.1")
    
    Returns:
        tuple[bool, str]: (is_compatible, message)
    """
    try:
        client_parts = [int(x) for x in client_version.split('.')]
        min_parts = [int(x) for x in API_MIN_CLIENT_VERSION.split('.')]
        server_parts = [int(x) for x in __server_version__.split('.')]
        
        # Проверка минимальной версии клиента
        if client_parts < min_parts:
            return False, f"Требуется клиент версии {API_MIN_CLIENT_VERSION} или выше"
        
        # Проверка мажорной версии (должна совпадать)
        if client_parts[0] != server_parts[0]:
            return False, f"Несовместимые версии: клиент {client_version}, сервер {__server_version__}"
        
        return True, "Версии совместимы"
        
    except Exception as e:
        return False, f"Ошибка проверки версии: {str(e)}"
