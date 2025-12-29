"""
Weather API Endpoints
Эндпоинты погоды с серверным кешированием
"""

import hashlib
import json
from datetime import datetime
from typing import Optional

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from server.config import get_settings
from server.database.storage import DatabaseStorage, get_db

router = APIRouter(prefix="/api/weather", tags=["Weather"])
settings = get_settings()


def _make_cache_key(params: dict) -> str:
    """Build stable cache key for parameters"""
    # Serialize params in sorted order and hash to keep length small
    serialized = "&".join(f"{k}={params[k]}" for k in sorted(params.keys()))
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


@router.get("/current")
async def current_weather(
    city: Optional[str] = Query(None, description="Город, например 'Kyiv'"),
    lat: Optional[float] = Query(None, description="Широта"),
    lon: Optional[float] = Query(None, description="Долгота"),
    lang: str = Query("ru", description="Язык ответа"),
    units: str = Query("metric", description="Система единиц: metric/imperial"),
    force_refresh: bool = Query(False, description="Игнорировать кеш и обновить"),
    db: Session = Depends(get_db),
):
    """Получить текущую погоду (OpenWeather). Кешируется на заданный TTL."""
    if not settings.openweather_api_key:
        raise HTTPException(status_code=503, detail="OPENWEATHER_API_KEY не задан в конфигурации")

    if not city and (lat is None or lon is None):
        raise HTTPException(status_code=400, detail="Нужно указать 'city' или пары 'lat' и 'lon'")

    query_params = {"appid": settings.openweather_api_key, "units": units, "lang": lang}
    if city:
        query_params["q"] = city
    else:
        query_params["lat"] = lat
        query_params["lon"] = lon

    cache_key = _make_cache_key(query_params)
    ttl_seconds = max(60, settings.weather_cache_ttl_minutes * 60)
    storage = DatabaseStorage(db)

    if not force_refresh:
        cached = storage.get_cache("weather", cache_key)
        if cached:
            payload = json.loads(cached.data)
            payload["cached"] = True
            return JSONResponse(content=payload)

    url = f"{settings.openweather_base_url}/weather"
    async with httpx.AsyncClient(timeout=10) as client:
        try:
            resp = await client.get(url, params=query_params)
            resp.raise_for_status()
        except httpx.HTTPError as e:
            raise HTTPException(status_code=502, detail=f"Ошибка обращения к OpenWeather: {e}")

    data = resp.json()
    wrapped = {
        "source": "openweather",
        "requested_at": datetime.utcnow().isoformat(),
        "cached": False,
        "query": {k: v for k, v in query_params.items() if k != "appid"},
        "data": data,
    }

    # Save to cache
    storage.set_cache("weather", cache_key, json.dumps(wrapped, ensure_ascii=False), ttl_seconds)

    return JSONResponse(content=wrapped)
