"""Search adapter skeleton

Provides a simple interface for web-search providers. Real implementations
should subclass `SearchAdapter` and implement `search(query, limit)`.
"""
from typing import List, Dict, Any, Optional


class SearchAdapter:
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}

    def search(self, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        """Perform a search and return a list of result dicts.

        Default implementation returns an empty list. Concrete adapters:
        - SerpAPI adapter
        - Google Custom Search adapter
        - RSS/local fallback
        """
        return []


class RSSSearchAdapter(SearchAdapter):
    """Simple RSS-based fallback adapter (skeleton)."""

    def search(self, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        # TODO: implement RSS aggregation for query
        return []
