"""
News module for Arvis
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

import requests

from config.config import Config
from utils.logger import ModuleLogger


class NewsModule:
    """News module using Arvis Server (preferred) or WorldNewsAPI fallback"""

    def __init__(self, config: Config):
        self.config = config
        self.logger = ModuleLogger("NewsModule")

        self.api_key = config.get("news.api_key", "")
        # Основные эндпоинты World News API
        self.api_url_search = str(config.get("news.api_url", "https://api.worldnewsapi.com/search-news"))
        self.api_url_top = "https://api.worldnewsapi.com/top-news"
        self.country = config.get("news.country", "ua")
        self.language = config.get("news.language", "ru")
        self.page_size = 10

        self.session = requests.Session()
        self.request_timeout = 15

        # Server integration
        self.use_server = bool(config.get("security.auth.use_remote_server", False))
        self.server_url = str(
            config.get("security.auth.server_url", "http://127.0.0.1:8000") or "http://127.0.0.1:8000"
        )
        self.server_news_url = f"{self.server_url.rstrip('/')}/api/news/top-headlines"

    def _headers(self) -> Dict[str, str]:
        return {"x-api-key": str(self.api_key or "")}

    def get_news(
        self, query: Optional[str] = None, category: Optional[str] = None, country: Optional[str] = None
    ) -> str:
        """Get latest news"""
        # Try server endpoint first if enabled
        if self.use_server:
            try:
                params = {
                    "country": country or self.country,
                    "language": self.language,
                    "pageSize": self.page_size,
                }
                if query:
                    params["q"] = query
                if category:
                    params["category"] = category

                resp = self.session.get(self.server_news_url, params=params, timeout=self.request_timeout)
                if resp.status_code == 200:
                    payload = resp.json()
                    # Server returns wrapped payload with data field (NewsAPI compatible)
                    data = payload.get("data", payload)
                    return self._format_news_like_newsapi(data, query or category or "главные новости")
                else:
                    self.logger.warning(f"Server news error: {resp.status_code} - falling back to direct API")
            except Exception as e:
                self.logger.warning(f"Server news request failed: {e}. Falling back to direct API")
        # If server not used or failed, try providers in configured priority
        try:
            try:
                val = self.config.get_news_provider_priority()
                provider_priority = val if isinstance(val, list) else ["rss", "gnews", "newsapi"]
            except Exception:
                val = self.config.get("llm.providers.news_priority", ["rss", "gnews", "newsapi"])
                provider_priority = val if isinstance(val, list) else ["rss", "gnews", "newsapi"]

            for provider in provider_priority:
                if provider == "rss":
                    try:
                        res = self._get_news_from_rss(query, category, country)
                        if res:
                            return res
                    except Exception as e:
                        self.logger.warning(f"RSS provider failed: {e}")
                        continue

                if provider == "gnews":
                    try:
                        res = self._get_news_from_gnews(query, category, country)
                        if res:
                            return res
                    except Exception as e:
                        self.logger.warning(f"GNews provider failed: {e}")
                        continue

                if provider == "newsapi":
                    try:
                        res = self._get_news_from_worldnews(query, category, country)
                        if res:
                            return res
                    except Exception as e:
                        self.logger.warning(f"NewsAPI/WorldNews provider failed: {e}")
                        continue

            return "❌ Не удалось получить новости: все провайдеры не вернули данные."

        except Exception as e:
            self.logger.error(f"Error selecting news provider: {e}")
            return "❌ Ошибка при выборе провайдера новостей."

    def format_news_response(self, data: Dict[str, Any], topic: str) -> str:
        """Format WorldNewsAPI response into readable text"""
        try:
            # WorldNewsAPI возвращает:
            # - search-news: поле 'news' (список)
            # - top-news: поле 'top_news' (список кластеров с подсписками 'news')
            if "top_news" in data:
                clusters = data.get("top_news", [])
                # Берем по одной новости из каждого кластера
                aggregated = []
                for cl in clusters:
                    items = cl.get("news", [])
                    if items:
                        aggregated.append(items[0])
                articles = aggregated
                total_results = len(articles)
            else:
                articles = data.get("news", []) or data.get("articles", [])
                total_results = data.get("totalResults", len(articles))

            if not articles:
                return f"📰 Новостей по теме '{topic}' не найдено."

            response = f"📰 Последние новости - {topic}\n"
            response += f"📊 Найдено: {total_results} новостей\n\n"

            for i, article in enumerate(articles[:5], 1):
                title = article.get("title", "Без заголовка")
                description = article.get("summary") or article.get("description") or article.get("text", "")
                source = article.get("source_name") or article.get("source", {}).get("name", "Неизвестный источник")
                url = article.get("url") or article.get("link", "")
                published_at = article.get("publish_date") or article.get("publishedAt", "")

                # Format publication time
                if published_at:
                    try:
                        pub_time = datetime.fromisoformat(published_at.replace("Z", "+00:00"))
                        time_str = pub_time.strftime("%d.%m %H:%M")
                    except:
                        time_str = "Время неизвестно"
                else:
                    time_str = "Время неизвестно"

                response += f"📄 {i}. {title}\n"
                response += f"📅 {time_str} | 📡 {source}\n"

                if description:
                    # Limit description length
                    desc = description[:150] + "..." if len(description) > 150 else description
                    response += f"📝 {desc}\n"

                if url:
                    response += f"🔗 {url}\n"

                response += "\n"

            return response

        except Exception as e:
            self.logger.error(f"Error formatting news response: {e}")
            return "❌ Ошибка при обработке новостей."

    # ---- GNews integration ----
    def _get_news_from_gnews(self, query: Optional[str], category: Optional[str], country: Optional[str]) -> Optional[str]:
        """Fetch news using GNews API (gnews.io). Requires gnews API key in config: news.gnews_api_key or news.api_key."""
        gnews_key = self.config.get("news.gnews_api_key") or self.api_key
        if not gnews_key:
            raise RuntimeError("GNews API key not configured")

        base = "https://gnews.io/api/v4"
        params = {"token": gnews_key, "lang": self.language, "max": self.page_size}
        if country or self.country:
            params["country"] = (country or self.country)

        if query:
            url = f"{base}/search"
            params["q"] = query
        else:
            url = f"{base}/top-headlines"

        resp = self.session.get(url, params=params, timeout=self.request_timeout)
        if resp.status_code != 200:
            raise RuntimeError(f"GNews error: {resp.status_code}")

        payload = resp.json()
        articles = payload.get("articles", [])
        data = {"articles": articles, "totalResults": len(articles)}
        return self._format_news_like_newsapi(data, query or category or "главные новости")

    def _get_news_from_worldnews(self, query: Optional[str], category: Optional[str], country: Optional[str]) -> Optional[str]:
        """Use existing WorldNewsAPI endpoints (self.api_url_search / self.api_url_top).

        This mirrors previous direct calls to WorldNewsAPI which require self.api_key.
        """
        if not self.api_key:
            raise RuntimeError("WorldNewsAPI key not configured")

        try:
            if query:
                params = {"text": query, "language": self.language, "number": self.page_size}
                if country or self.country:
                    params["source-country"] = country or self.country
                response = self.session.get(
                    self.api_url_search, params=params, headers=self._headers(), timeout=self.request_timeout
                )
            else:
                params = {"language": self.language, "source-country": (country or self.country)}
                response = self.session.get(
                    self.api_url_top, params=params, headers=self._headers(), timeout=self.request_timeout
                )

            if response.status_code == 200:
                data = response.json()
                return self.format_news_response(data, query or category or "главные новости")
            else:
                raise RuntimeError(f"WorldNewsAPI returned {response.status_code}")

        except Exception:
            raise

    # ---- RSS fallback ----
    def _get_news_from_rss(self, query: Optional[str], category: Optional[str], country: Optional[str]) -> Optional[str]:
        """Aggregate RSS feeds configured in `news.rss_sources` and return top articles.

        Config key: `news.rss_sources` - list of feed URLs.
        """
        try:
            sources = self.config.get("news.rss_sources", []) or []
            if not isinstance(sources, list) or not sources:
                raise RuntimeError("RSS sources not configured")

            articles = []
            import xml.etree.ElementTree as ET

            for feed in sources:
                try:
                    r = self.session.get(feed, timeout=self.request_timeout)
                    if r.status_code != 200:
                        continue
                    root = ET.fromstring(r.content)
                    # Typical RSS structure: /rss/channel/item
                    for item in root.findall('.//item')[: self.page_size]:
                        title = item.findtext('title') or ''
                        link = item.findtext('link') or ''
                        desc = item.findtext('description') or ''
                        pub = item.findtext('pubDate') or ''
                        articles.append({
                            'title': title,
                            'description': desc,
                            'url': link,
                            'publishedAt': pub,
                            'source': {'name': feed},
                        })
                except Exception:
                    continue

            if not articles:
                return None

            data = {"articles": articles, "totalResults": len(articles)}
            return self._format_news_like_newsapi(data, query or category or "главные новости")
        except Exception as e:
            raise

    def _format_news_like_newsapi(self, data: Dict[str, Any], topic: str) -> str:
        """Format response shaped like NewsAPI (articles + totalResults)."""
        try:
            articles = data.get("articles", [])
            total_results = data.get("totalResults", len(articles))

            if not articles:
                return f"📰 Новостей по теме '{topic}' не найдено."

            response = f"📰 Последние новости - {topic}\n"
            response += f"📊 Найдено: {total_results} новостей\n\n"

            for i, article in enumerate(articles[:5], 1):
                title = article.get("title", "Без заголовка")
                description = article.get("description", "")
                source = (article.get("source") or {}).get("name", "Неизвестный источник")
                url = article.get("url", "")
                published_at = article.get("publishedAt", "")

                # Format publication time
                if published_at:
                    try:
                        pub_time = datetime.fromisoformat(published_at.replace("Z", "+00:00"))
                        time_str = pub_time.strftime("%d.%m %H:%M")
                    except:
                        time_str = "Время неизвестно"
                else:
                    time_str = "Время неизвестно"

                response += f"📄 {i}. {title}\n"
                response += f"📅 {time_str} | 📡 {source}\n"

                if description:
                    desc = description[:150] + "..." if len(description) > 150 else description
                    response += f"📝 {desc}\n"

                if url:
                    response += f"🔗 {url}\n"

                response += "\n"

            return response
        except Exception as e:
            self.logger.error(f"Error formatting NewsAPI-like response: {e}")
            return "❌ Ошибка при обработке новостей."

    def get_news_by_category(self, category: str) -> str:
        """Get news by specific category"""
        valid_categories = ["business", "entertainment", "general", "health", "science", "sports", "technology"]

        if category.lower() not in valid_categories:
            return f"❌ Неверная категория. Доступные: {', '.join(valid_categories)}"

        return self.get_news(category=category.lower())

    def search_news(self, query: str, sort_by: str = "publish_date") -> str:
        """Search news by query (WorldNewsAPI)"""
        if not self.api_key:
            return "❌ API ключ для новостей не настроен."
        try:
            params = {"text": query, "language": self.language, "number": self.page_size, "sort": "publish-time"}
            response = self.session.get(
                self.api_url_search, params=params, headers=self._headers(), timeout=self.request_timeout
            )
            if response.status_code == 200:
                data = response.json()
                return self.format_news_response(data, f"поиск: {query}")
            else:
                return f"❌ Ошибка поиска новостей: {response.status_code}"
        except Exception as e:
            self.logger.error(f"News search error: {e}")
            return f"❌ Ошибка поиска: {str(e)}"

    def get_sources(self, category: Optional[str] = None, country: Optional[str] = None) -> str:
        """Get available news sources"""
        if not self.api_key:
            return "❌ API ключ для новостей не настроен."

        try:
            sources_url = "https://newsapi.org/v2/sources"

            params = {"apiKey": self.api_key, "language": self.language}

            if category:
                params["category"] = category
            if country:
                params["country"] = country

            response = self.session.get(sources_url, params=params)

            if response.status_code == 200:
                data = response.json()
                sources = data.get("sources", [])

                if not sources:
                    return "📡 Источники новостей не найдены."

                response_text = "📡 Доступные источники новостей:\n\n"

                for source in sources[:10]:
                    name = source.get("name", "")
                    description = source.get("description", "")
                    category = source.get("category", "")
                    url = source.get("url", "")

                    response_text += f"📰 {name}\n"
                    if category:
                        response_text += f"📂 Категория: {category}\n"
                    if description:
                        desc = description[:100] + "..." if len(description) > 100 else description
                        response_text += f"📝 {desc}\n"
                    if url:
                        response_text += f"🔗 {url}\n"
                    response_text += "\n"

                return response_text
            else:
                return f"❌ Ошибка получения источников: {response.status_code}"

        except Exception as e:
            self.logger.error(f"Sources API error: {e}")
            return f"❌ Ошибка: {str(e)}"

    def get_regional_news(self, region: Optional[str] = None) -> str:
        """Get regional news"""
        region_map = {
            "украина": "ua",
            "россия": "ru",
            "польша": "pl",
            "германия": "de",
            "франция": "fr",
            "великобритания": "gb",
            "сша": "us",
        }

        if region:
            country_code = str(region_map.get(region.lower(), region.lower()))
        else:
            country_code = self.country

        return self.get_news(country=str(country_code))

    def set_api_key(self, api_key: str):
        """Set news API key"""
        self.api_key = api_key
        self.config.set("news.api_key", api_key)
        self.logger.info("News API key updated")

    def set_country(self, country: str):
        """Set default country for news"""
        self.country = country
        self.config.set("news.country", country)
        self.logger.info(f"Default country set to: {country}")

    def set_language(self, language: str):
        """Set language for news"""
        self.language = language
        self.config.set("news.language", language)
        self.logger.info(f"Language set to: {language}")

    def test_api_connection(self) -> bool:
        """Test news API connection"""
        if not self.api_key:
            return False
        try:
            params = {"language": self.language, "source-country": self.country}
            response = self.session.get(
                self.api_url_top, params=params, headers=self._headers(), timeout=self.request_timeout
            )
            return response.status_code == 200
        except Exception as e:
            self.logger.error(f"News API test failed: {e}")
            return False

    def get_trending_topics(self) -> str:
        """Get trending news topics (simplified implementation)"""
        trending_queries = ["технологии", "политика", "экономика", "спорт", "наука", "здоровье", "развлечения"]

        results = []
        for query in trending_queries[:3]:  # Limit to avoid API rate limits
            try:
                response = self.search_news(query)
                if not response.startswith("❌"):
                    results.append(f"🔥 {query.capitalize()}")
                    # Get first headline from response
                    lines = response.split("\n")
                    for line in lines:
                        if line.startswith("📄 1."):
                            headline = line.replace("📄 1. ", "")
                            results.append(f"   • {headline[:80]}...")
                            break
            except:
                continue

        if results:
            return "🔥 Актуальные темы:\n\n" + "\n".join(results)
        else:
            return "❌ Не удалось получить актуальные темы."

    def cleanup(self):
        """Cleanup news module resources"""
        try:
            if self.session:
                self.session.close()
            self.logger.info("News module cleanup complete")
        except Exception as e:
            self.logger.error(f"Error during news cleanup: {e}")

    def get_status(self) -> Dict[str, Any]:
        """Get news module status"""
        return {
            "api_key_configured": bool(self.api_key),
            "country": self.country,
            "language": self.language,
            "api_connection": self.test_api_connection(),
        }
