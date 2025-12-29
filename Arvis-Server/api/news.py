"""
News API Endpoints
Эндпоинты новостей с серверным кешированием
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

router = APIRouter(prefix="/api/news", tags=["News"])
settings = get_settings()


def _make_cache_key(params: dict) -> str:
    """Build stable cache key for parameters"""
    serialized = "&".join(f"{k}={params[k]}" for k in sorted(params.keys()))
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


@router.get("/top-headlines")
async def top_headlines(
    country: Optional[str] = Query("ua", description="Страна (2-буквенный код)"),
    q: Optional[str] = Query(None, description="Поисковый запрос"),
    category: Optional[str] = Query(None, description="Категория новостей"),
    language: Optional[str] = Query("ru", description="Язык"),
    pageSize: int = Query(10, ge=1, le=100, description="Количество результатов"),
    force_refresh: bool = Query(False, description="Игнорировать кеш и обновить"),
    db: Session = Depends(get_db),
):
    """Получить заголовки новостей (NewsAPI). Кешируется на заданный TTL."""
    if not settings.newsapi_api_key:
        raise HTTPException(status_code=503, detail="NEWSAPI_API_KEY не задан в конфигурации")

    params = {"apiKey": settings.newsapi_api_key, "pageSize": pageSize}
    if country:
        params["country"] = country
    if language:
        params["language"] = language
    if q:
        params["q"] = q
    if category:
        params["category"] = category

    cache_key = _make_cache_key({k: v for k, v in params.items() if k != "apiKey"})
    ttl_seconds = max(60, settings.news_cache_ttl_minutes * 60)
    storage = DatabaseStorage(db)

    if not force_refresh:
        cached = storage.get_cache("news", cache_key)
        if cached:
            payload = json.loads(cached.data)
            payload["cached"] = True
            return JSONResponse(content=payload)

    url = f"{settings.newsapi_base_url}/top-headlines"
    async with httpx.AsyncClient(timeout=10) as client:
        try:
            resp = await client.get(url, params=params)
            resp.raise_for_status()
        except httpx.HTTPError as e:
            raise HTTPException(status_code=502, detail=f"Ошибка обращения к NewsAPI: {e}")

    data = resp.json()
    wrapped = {
        "source": "newsapi",
        "requested_at": datetime.utcnow().isoformat(),
        "cached": False,
        "query": {k: v for k, v in params.items() if k != "apiKey"},
        "data": data,
    }

    storage.set_cache("news", cache_key, json.dumps(wrapped, ensure_ascii=False), ttl_seconds)
    return JSONResponse(content=wrapped)
