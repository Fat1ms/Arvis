"""
API module initialization
Инициализация модуля API
"""

# IMPORTANT:
# Do NOT import `server.api` here.
# `server.api` imports submodules like `api.auth`, which causes a circular import
# if `api.__init__` imports `server.api`.

__all__ = []
