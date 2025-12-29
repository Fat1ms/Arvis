"""
Compatibility layer for server.api
Re-exports modules from top-level 'api' package.
"""
import importlib

# Expose submodules as attributes so 'from server.api import <module>' works
auth = importlib.import_module("api.auth")
users = importlib.import_module("api.users")
weather = importlib.import_module("api.weather")
news = importlib.import_module("api.news")

# New commerce/download modules
billing = importlib.import_module("api.billing")
downloads = importlib.import_module("api.downloads")

__all__ = ["auth", "users", "weather", "news", "billing", "downloads"]
