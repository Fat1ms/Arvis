"""Провайдеры данных (search/news/weather) - адаптеры

Этот пакет содержит простые адаптеры-переключатели между провайдерами.
Адаптеры реализованы как скелеты: они дают единый интерфейс и не выполняют
фактических сетевых вызовов по умолчанию (чтобы избежать зависимостей).
"""

from .search_adapter import SearchAdapter
from .news_adapter import NewsAdapter
from .weather_adapter import WeatherAdapter

__all__ = ["SearchAdapter", "NewsAdapter", "WeatherAdapter"]
