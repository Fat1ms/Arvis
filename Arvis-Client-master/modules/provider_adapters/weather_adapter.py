"""Weather adapter skeleton

Provides a simple interface for weather providers. Default provider is
Open-Meteo (recommended free option).
"""
from typing import Dict, Any, Optional


class WeatherAdapter:
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}

    def get_current_weather(self, latitude: float, longitude: float) -> Dict[str, Any]:
        """Return a dict with current weather data.

        Default implementation returns an empty dict. Implementations may call
        Open-Meteo or OpenWeatherMap.
        """
        return {}


class OpenMeteoAdapter(WeatherAdapter):
    def get_current_weather(self, latitude: float, longitude: float) -> Dict[str, Any]:
        # TODO: implement simple HTTP call to Open-Meteo (or local cache)
        return {}
