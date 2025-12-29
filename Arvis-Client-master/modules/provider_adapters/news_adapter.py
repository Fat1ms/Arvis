"""News adapter skeleton

Provides an interface for fetching news articles. Implementations may use
GNews, NewsAPI, or RSS feeds.
"""
from typing import List, Dict, Any, Optional


class NewsAdapter:
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}

    def get_top_headlines(self, topic: str = "world", limit: int = 10) -> List[Dict[str, Any]]:
        """Return a list of news articles (dicts with title, url, source, published_at).
        Default implementation returns an empty list.
        """
        return []


class RSSNewsAdapter(NewsAdapter):
    def get_top_headlines(self, topic: str = "world", limit: int = 10) -> List[Dict[str, Any]]:
        # TODO: implement simple RSS feed aggregation
        return []
