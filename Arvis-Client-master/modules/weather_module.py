"""
Weather module for Arvis
"""

from datetime import datetime
from typing import Any, Dict, Optional

import requests

from config.config import Config
from utils.logger import ModuleLogger


class WeatherModule:
    """Weather information module using OpenWeatherMap API"""

    def __init__(self, config: Config):
        self.config = config
        self.logger = ModuleLogger("WeatherModule")

        self.api_key = config.get("weather.api_key", "")
        self.api_url = str(config.get("weather.api_url", "http://api.openweathermap.org/data/2.5/weather"))
        self.default_city = config.get("weather.default_city", "Kyiv")
        self.units = "metric"  # Celsius
        self.lang = "ru"
        self.brief = config.get("weather.brief", True)

        # Server integration
        self.use_server = bool(config.get("security.auth.use_remote_server", False))
        self.server_url = str(config.get("security.auth.server_url", "http://127.0.0.1:8000") or "http://127.0.0.1:8000")
        self.server_weather_url = f"{self.server_url.rstrip('/')}/api/weather/current"

        self.session = requests.Session()
        self.request_timeout = 10
        # Provider preference (may include 'open_meteo', 'openweathermap')
        try:
            val = config.get_weather_provider_priority()
            self.provider_priority = val if isinstance(val, list) else ["open_meteo", "openweathermap"]
        except Exception:
            val = self.config.get("llm.providers.weather_priority", ["open_meteo", "openweathermap"])
            self.provider_priority = val if isinstance(val, list) else ["open_meteo", "openweathermap"]

        # offline_mode flag
        try:
            self.offline_mode = bool(self.config.is_offline_mode())
        except Exception:
            self.offline_mode = bool(self.config.get("llm.offline_mode", False))

    def get_weather(self, city: Optional[str] = None) -> str:
        """Get current weather information"""
        target_city = city or self.default_city

        # Prefer server endpoint if enabled
        if self.use_server:
            try:
                params = {"city": target_city, "units": self.units, "lang": self.lang}
                resp = self.session.get(self.server_weather_url, params=params, timeout=self.request_timeout)
                if resp.status_code == 200:
                    payload = resp.json()
                    data = payload.get("data", payload)
                    return self.format_weather_brief_response(data) if self.brief else self.format_weather_response(data)
                else:
                    # If server failed, fall back to direct API (if key configured)
                    self.logger.warning(f"Server weather error: {resp.status_code} - falling back to direct API")
            except Exception as e:
                self.logger.warning(f"Server weather request failed: {e}. Falling back to direct API")

        # Try providers according to priority
        for provider in self.provider_priority:
            if provider == "open_meteo":
                try:
                    # Open-Meteo doesn't require API key
                    return self._get_weather_open_meteo(str(target_city))
                except Exception as e:
                    self.logger.warning(f"Open-Meteo provider failed: {e}")
                    continue

            if provider == "openweathermap":
                # OpenWeatherMap requires API key
                if not self.api_key:
                    self.logger.debug("OpenWeatherMap skipped: API key not configured")
                    continue
                try:
                    self.logger.info(f"Getting weather (OpenWeatherMap) for {target_city}")
                    params = {"q": target_city, "appid": self.api_key, "units": self.units, "lang": self.lang}
                    response = self.session.get(self.api_url, params=params, timeout=self.request_timeout)
                    if response.status_code == 200:
                        data = response.json()
                        return self.format_weather_brief_response(data) if self.brief else self.format_weather_response(data)
                    elif response.status_code == 401:
                        return "❌ Неверный API ключ для погоды. Проверьте настройки."
                    elif response.status_code == 404:
                        return f"❌ Город '{target_city}' не найден. Проверьте название города."
                    else:
                        self.logger.warning(f"OpenWeatherMap returned status {response.status_code}")
                        continue
                except requests.exceptions.Timeout:
                    return "❌ Превышено время ожидания при запросе погоды."
                except requests.exceptions.ConnectionError:
                    return "❌ Нет подключения к интернету для получения погоды."
                except Exception as e:
                    self.logger.error(f"Weather API error (OpenWeatherMap): {e}")
                    continue

        return "❌ Не удалось получить погоду: все провайдеры не вернули данные."

    # ---- Open-Meteo implementation ----
    def _get_weather_open_meteo(self, city: str) -> str:
        """Use Open-Meteo geocoding + current_weather endpoint to get simple weather info."""
        # Resolve coordinates via Open-Meteo geocoding
        try:
            geocode_url = "https://geocoding-api.open-meteo.com/v1/search"
            params = {"name": city, "count": 1, "language": "ru"}
            resp = self.session.get(geocode_url, params=params, timeout=self.request_timeout)
            if resp.status_code != 200:
                raise RuntimeError(f"Geocoding failed: {resp.status_code}")
            geo = resp.json()
            results = geo.get("results") or []
            if not results:
                raise RuntimeError("Город не найден в Open-Meteo geocoding")

            loc = results[0]
            lat = loc.get("latitude")
            lon = loc.get("longitude")
            name = loc.get("name")

            # Get current weather
            weather_url = "https://api.open-meteo.com/v1/forecast"
            params = {"latitude": lat, "longitude": lon, "current_weather": True, "timezone": "auto"}
            wresp = self.session.get(weather_url, params=params, timeout=self.request_timeout)
            if wresp.status_code != 200:
                raise RuntimeError(f"Open-Meteo weather failed: {wresp.status_code}")
            wdata = wresp.json()
            current = wdata.get("current_weather") or {}

            # Map weathercode to human description (simple mapping)
            code = int(current.get("weathercode", -1))
            desc = self._open_meteo_code_to_text(code)
            temp = current.get("temperature")
            wind = current.get("windspeed")
            time = current.get("time")

            # Format brief response
            city_display = name or city
            weather_emoji = self.get_weather_emoji_from_code(code)
            temp_str = f"{round(temp)}°C" if temp is not None else "N/A"
            wind_str = f"{wind} м/с" if wind is not None else "N/A"
            response = f"{city_display}, {weather_emoji} {desc}\n🌡️ Температура: {temp_str}\n💨 Ветер: {wind_str}\n⏱️ {time}"
            return response
        except requests.exceptions.Timeout:
            return "❌ Превышено время ожидания при запросе к Open-Meteo."
        except requests.exceptions.ConnectionError:
            return "❌ Нет подключения к интернету для получения погоды (Open-Meteo)."
        except Exception as e:
            self.logger.error(f"Open-Meteo error: {e}")
            raise

    def _open_meteo_code_to_text(self, code: int) -> str:
        mapping = {
            0: "Ясно",
            1: "Преимущественно ясно",
            2: "Малооблачно",
            3: "Облачно",
            45: "Туман",
            48: "Иней",
            51: "Лёгкая морось",
            53: "Умеренная морось",
            55: "Сильная морось",
            61: "Небольшой дождь",
            63: "Умеренный дождь",
            65: "Сильный дождь",
            71: "Небольшой снег",
            73: "Умеренный снег",
            75: "Сильный снег",
            95: "Гроза",
        }
        return mapping.get(code, "Неизвестная погода")

    def get_weather_emoji_from_code(self, code: int) -> str:
        # Reuse simple emoji mapping used earlier
        if 200 <= code < 300:
            return "⛈️"
        if 300 <= code < 600:
            return "🌧️"
        if 600 <= code < 700:
            return "❄️"
        if code == 800:
            return "☀️"
        if 801 <= code < 900:
            return "☁️"
        return "🌤️"

    def format_weather_response(self, data: Dict[str, Any]) -> str:
        """Format weather API response into readable text"""
        try:
            city = data["name"]
            country = data["sys"]["country"]

            # Main weather info
            main = data["main"]
            weather = data["weather"][0]
            wind = data.get("wind", {})

            temperature = round(main["temp"])
            feels_like = round(main["feels_like"])
            humidity = main["humidity"]
            pressure = main["pressure"]

            description = weather["description"].capitalize()
            wind_speed = wind.get("speed", 0)

            # Sunrise/sunset
            sunrise = datetime.fromtimestamp(data["sys"]["sunrise"]).strftime("%H:%M")
            sunset = datetime.fromtimestamp(data["sys"]["sunset"]).strftime("%H:%M")

            # Weather emoji based on weather code
            weather_emoji = self.get_weather_emoji(weather["id"])

            # Format response
            response = f"""🌍 Погода в городе {city}, {country}

{weather_emoji} {description}
🌡️ Температура: {temperature}°C (ощущается как {feels_like}°C)
💧 Влажность: {humidity}%
📊 Давление: {pressure} гПа
💨 Ветер: {wind_speed} м/с

🌅 Восход: {sunrise}
🌇 Закат: {sunset}"""

            return response

        except KeyError as e:
            self.logger.error(f"Missing key in weather response: {e}")
            return "❌ Неполные данные о погоде получены от сервера."
        except Exception as e:
            self.logger.error(f"Error formatting weather response: {e}")
            return "❌ Ошибка при обработке данных о погоде."

    def format_weather_brief_response(self, data: Dict[str, Any]) -> str:
        """Compact weather output: City, condition emoji+text, temperature with feels like."""
        try:
            city = data["name"]
            # Main weather info
            main = data["main"]
            weather = data["weather"][0]
            temperature = round(main["temp"])
            feels_like = round(main["feels_like"])
            description = weather["description"].capitalize()
            weather_emoji = self.get_weather_emoji(weather["id"])

            # Example: "Киев, ☁️ Пасмурно\n🌡️ Температура: 10°C (ощущается как 10°C)"
            return (
                f"{city}, {weather_emoji} {description}\n🌡️ Температура: {temperature}°C (ощущается как {feels_like}°C)"
            )
        except Exception as e:
            self.logger.error(f"Error formatting brief weather: {e}")
            return self.format_weather_response(data)

    def get_weather_emoji(self, weather_code: int) -> str:
        """Get emoji based on OpenWeatherMap weather code"""
        if 200 <= weather_code < 300:  # Thunderstorm
            return "⛈️"
        elif 300 <= weather_code < 400:  # Drizzle
            return "🌦️"
        elif 500 <= weather_code < 600:  # Rain
            return "🌧️"
        elif 600 <= weather_code < 700:  # Snow
            return "❄️"
        elif 700 <= weather_code < 800:  # Atmosphere (fog, mist, etc.)
            return "🌫️"
        elif weather_code == 800:  # Clear sky
            return "☀️"
        elif 801 <= weather_code < 900:  # Clouds
            return "☁️"
        else:
            return "🌤️"

    def get_forecast(self, city: Optional[str] = None, days: int = 5) -> str:
        """Get weather forecast (requires different API endpoint)"""
        if not self.api_key:
            return "❌ API ключ для погоды не настроен."

        target_city = city or self.default_city

        try:
            self.logger.info(f"Getting forecast for {target_city}")

            # Use forecast endpoint
            forecast_url = "http://api.openweathermap.org/data/2.5/forecast"
            params = {
                "q": target_city,
                "appid": self.api_key,
                "units": self.units,
                "lang": self.lang,
                "cnt": days * 8,  # 8 forecasts per day (every 3 hours)
            }

            response = self.session.get(forecast_url, params=params)

            if response.status_code == 200:
                data = response.json()
                return self.format_forecast_response(data, days)
            else:
                return f"❌ Ошибка получения прогноза: {response.status_code}"

        except Exception as e:
            self.logger.error(f"Forecast API error: {e}")
            return f"❌ Ошибка при получении прогноза: {str(e)}"

    def format_forecast_response(self, data: Dict[str, Any], days: int) -> str:
        """Format forecast API response"""
        try:
            city = data["city"]["name"]
            country = data["city"]["country"]

            response = f"📅 Прогноз погоды для {city}, {country}:\n\n"

            # Group forecasts by day
            daily_forecasts = {}
            for item in data["list"][: days * 8]:
                date = datetime.fromtimestamp(item["dt"]).date()
                if date not in daily_forecasts:
                    daily_forecasts[date] = []
                daily_forecasts[date].append(item)

            # Format each day
            for date, forecasts in list(daily_forecasts.items())[:days]:
                day_name = date.strftime("%d.%m (%A)")

                # Get min/max temperatures for the day
                temps = [f["main"]["temp"] for f in forecasts]
                min_temp = round(min(temps))
                max_temp = round(max(temps))

                # Get most common weather condition
                weather_codes = [f["weather"][0]["id"] for f in forecasts]
                most_common_code = max(set(weather_codes), key=weather_codes.count)
                weather_emoji = self.get_weather_emoji(most_common_code)

                response += f"{weather_emoji} {day_name}: {min_temp}°C...{max_temp}°C\n"

            return response

        except Exception as e:
            self.logger.error(f"Error formatting forecast: {e}")
            return "❌ Ошибка при обработке прогноза погоды."

    def set_api_key(self, api_key: str):
        """Set weather API key"""
        self.api_key = api_key
        self.config.set("weather.api_key", api_key)
        self.logger.info("Weather API key updated")

    def set_default_city(self, city: str):
        """Set default city for weather"""
        self.default_city = city
        self.config.set("weather.default_city", city)
        self.logger.info(f"Default city set to: {city}")

    def test_api_connection(self) -> bool:
        """Test weather API connection"""
        if not self.api_key:
            return False

        try:
            params = {"q": "London", "appid": self.api_key, "units": self.units}

            response = self.session.get(self.api_url, params=params, timeout=self.request_timeout)
            return response.status_code == 200

        except Exception as e:
            self.logger.error(f"API test failed: {e}")
            return False

    def get_weather_by_coordinates(self, lat: float, lon: float) -> str:
        """Get weather by coordinates"""
        # Prefer server endpoint if enabled
        if self.use_server:
            try:
                params = {"lat": lat, "lon": lon, "units": self.units, "lang": self.lang}
                resp = self.session.get(self.server_weather_url, params=params, timeout=self.request_timeout)
                if resp.status_code == 200:
                    payload = resp.json()
                    data = payload.get("data", payload)
                    return self.format_weather_response(data)
                else:
                    self.logger.warning(f"Server weather (coords) error: {resp.status_code} - fallback to direct API")
            except Exception as e:
                self.logger.warning(f"Server weather (coords) failed: {e}. Falling back to direct API")

        if not self.api_key:
            return "❌ API ключ для погоды не настроен."

        try:
            params = {"lat": lat, "lon": lon, "appid": self.api_key, "units": self.units, "lang": self.lang}

            response = self.session.get(self.api_url, params=params, timeout=self.request_timeout)

            if response.status_code == 200:
                data = response.json()
                return self.format_weather_response(data)
            else:
                return f"❌ Ошибка получения погоды по координатам: {response.status_code}"

        except Exception as e:
            self.logger.error(f"Weather by coordinates error: {e}")
            return f"❌ Ошибка: {str(e)}"

    def cleanup(self):
        """Cleanup weather module resources"""
        try:
            if self.session:
                self.session.close()
            self.logger.info("Weather module cleanup complete")
        except Exception as e:
            self.logger.error(f"Error during weather cleanup: {e}")

    def get_status(self) -> Dict[str, Any]:
        """Get weather module status"""
        return {
            "api_key_configured": bool(self.api_key),
            "default_city": self.default_city,
            "api_connection": self.test_api_connection(),
        }
