"""Google Custom Search integration for Arvis."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

import requests

from utils.logger import ModuleLogger
from utils.security import AuditEventType, AuditSeverity, Permission, get_audit_logger, get_rbac_manager


class SearchModule:
    """Simple wrapper around Google Custom Search API."""

    _BASE_URL = "https://www.googleapis.com/customsearch/v1"

    def __init__(self, config):
        self.config = config
        self.logger = ModuleLogger("SearchModule")

        # RBAC и Audit (v1.4.0: Phase 2)
        self.rbac_enabled = bool(
            self.config.get("security.rbac.enabled", self.config.get("security.rbac_enabled", False))
        )
        self.rbac = get_rbac_manager() if self.rbac_enabled else None
        self.audit = get_audit_logger(config)
        self.current_user = None

    def set_current_user(self, user_id: Optional[str]):
        """Установить текущего пользователя для RBAC проверок"""
        self.current_user = user_id
        if self.rbac:
            self.rbac.set_current_user(user_id)

    # ------------------------------------------------------------------
    # Public helpers
    # ------------------------------------------------------------------
    def is_enabled(self) -> bool:
        """Return True if web search integration is enabled and configured."""
        if not bool(self.config.get("search.enabled", True)):
            return False
        if not self._api_key or not self._engine_id:
            return False
        return True

    def should_handle(self, message: str) -> bool:
        """Heuristic to decide whether the query should trigger web search."""
        if not message:
            return False
        lowered = message.lower()

        # ИСКЛЮЧАЕМ запросы, относящиеся к встроенным модулям
        exclusions = (
            "погода",
            "температура",
            "weather",
            "новости",
            "news",
            "запусти",
            "открой",
            "включи",
            "выключи",
            "громкость",
            "звук",
            "музыка",
            "календарь",
            "напомни",
            "событие",
        )
        if any(word in lowered for word in exclusions):
            return False

        # Триггеры для веб-поиска
        triggers = (
            "найди",
            "поиск",
            "поищи",
            "загугли",
            "google",
            "гугл",
            "в интернете",
            "найди информацию",
        )
        return any(word in lowered for word in triggers)

    def search(self, message: str) -> Optional[Dict[str, Any]]:
        """Perform Google Custom Search request and return structured results."""
        # RBAC: проверка разрешений
        if self.rbac and not self.rbac.has_permission(Permission.MODULE_SEARCH):
            self.audit.log_event(
                event_type=AuditEventType.PERMISSION_DENIED,
                action="web_search",
                user_id=self.current_user,
                severity=AuditSeverity.WARNING,
                details={"module": "search", "query": message[:50]},
                success=False,
            )
            self.logger.warning(f"Access denied for user {self.current_user} to search module")
            return None

        if not self.is_enabled():
            self.logger.debug("Search module is disabled or misconfigured")
            return None

        query = self._extract_query(message)
        if not query:
            query = message.strip()
        if not query:
            return None

        params = {
            "key": self._api_key,
            "cx": self._engine_id,
            "q": query,
            "num": self._results_limit,
        }
        region = self.config.get("search.region", "")
        if region:
            params["gl"] = region

        try:
            response = requests.get(self._BASE_URL, params=params, timeout=6)
            response.raise_for_status()
            data = response.json()
        except requests.RequestException as exc:
            self.logger.error(f"Search request failed: {exc}")
            return {
                "query": query,
                "results": [],
                "error": str(exc),
                "requested_at": datetime.utcnow().isoformat(),
            }

        items = data.get("items", []) or []
        results = []
        for item in items[: self._results_limit]:
            title = item.get("title") or item.get("htmlTitle") or ""
            link = item.get("link") or ""
            snippet = item.get("snippet") or item.get("htmlSnippet") or ""
            display_link = item.get("displayLink") or ""
            if not link:
                continue
            results.append(
                {
                    "title": title.strip(),
                    "link": link.strip(),
                    "display_link": display_link.strip() or link.strip(),
                    "snippet": (snippet or "").replace("\n", " ").strip(),
                }
            )

        context = self._format_context(results)
        return {
            "query": query,
            "results": results,
            "context": context,
            "requested_at": datetime.utcnow().isoformat(),
            "total_results": data.get("searchInformation", {}).get("totalResults"),
        }

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    @property
    def _api_key(self) -> str:
        return str(self.config.get("search.api_key", "") or "").strip()

    @property
    def _engine_id(self) -> str:
        return str(self.config.get("search.engine_id", "") or "").strip()

    @property
    def _results_limit(self) -> int:
        limit = self.config.get("search.results_limit", 3)
        try:
            value = int(limit)
            return max(1, min(value, 5))
        except Exception:
            return 3

    def _extract_query(self, message: str) -> str:
        cleaned = message
        replacements = (
            ("найди в интернете", ""),
            ("поищи в интернете", ""),
            ("загугли", ""),
            ("найди", ""),
            ("поищи", ""),
            ("google", ""),
            ("гугл", ""),
            ("поиск", ""),
            ("в интернете", ""),
        )
        for phrase, substitute in replacements:
            cleaned = cleaned.replace(phrase, substitute)
            cleaned = cleaned.replace(phrase.capitalize(), substitute)
        return " ".join(cleaned.split()).strip(" ,:?\u2014")

    def _format_context(self, results: List[Dict[str, str]]) -> str:
        if not results:
            return ""
        lines = ["Интернет-результаты:"]
        for idx, item in enumerate(results, start=1):
            title = item.get("title") or item.get("display_link") or ""
            snippet = item.get("snippet", "")
            link = item.get("link", "")
            if snippet:
                lines.append(f"{idx}. {title}: {snippet} (URL: {link})")
            else:
                lines.append(f"{idx}. {title} (URL: {link})")
        return "\n".join(lines)
