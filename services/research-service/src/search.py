"""
Web Search Module

Provides web search functionality using multiple search engines.
"""

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

import httpx
from duckduckgo_search import DDGS

logger = logging.getLogger(__name__)


class SearchEngine(str, Enum):
    """Supported search engines."""
    DUCKDUCKGO = "duckduckgo"
    BRAVE = "brave"
    SERPAPI = "serpapi"


@dataclass
class SearchResult:
    """A search result."""
    title: str
    url: str
    snippet: str
    source: str
    position: int
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SearchResponse:
    """Response from a search query."""
    query: str
    engine: SearchEngine
    results: List[SearchResult]
    total_results: int
    search_time_ms: float


class WebSearcher:
    """
    Web search engine abstraction.

    Supports multiple search backends with fallback.
    """

    def __init__(
        self,
        default_engine: str = "duckduckgo",
        brave_api_key: Optional[str] = None,
        serpapi_key: Optional[str] = None,
        timeout: int = 30,
        max_results: int = 10,
    ):
        self.default_engine = SearchEngine(default_engine)
        self.brave_api_key = brave_api_key
        self.serpapi_key = serpapi_key
        self.timeout = timeout
        self.max_results = max_results

    async def search(
        self,
        query: str,
        engine: Optional[SearchEngine] = None,
        max_results: Optional[int] = None,
        region: str = "wt-wt",  # Worldwide
        safe_search: str = "moderate",
    ) -> SearchResponse:
        """
        Search the web.

        Args:
            query: Search query
            engine: Search engine to use (default: configured default)
            max_results: Maximum results to return
            region: Region code for results
            safe_search: Safe search level (off, moderate, strict)

        Returns:
            SearchResponse with results
        """
        engine = engine or self.default_engine
        max_results = max_results or self.max_results

        start_time = datetime.utcnow()

        try:
            if engine == SearchEngine.DUCKDUCKGO:
                results = await self._search_duckduckgo(query, max_results, region, safe_search)
            elif engine == SearchEngine.BRAVE:
                results = await self._search_brave(query, max_results, region)
            elif engine == SearchEngine.SERPAPI:
                results = await self._search_serpapi(query, max_results, region)
            else:
                # Fallback to DuckDuckGo
                results = await self._search_duckduckgo(query, max_results, region, safe_search)

            search_time = (datetime.utcnow() - start_time).total_seconds() * 1000

            return SearchResponse(
                query=query,
                engine=engine,
                results=results,
                total_results=len(results),
                search_time_ms=search_time,
            )

        except Exception as e:
            logger.error(f"Search error ({engine}): {e}")
            # Try fallback
            if engine != SearchEngine.DUCKDUCKGO:
                logger.info("Falling back to DuckDuckGo")
                return await self.search(
                    query, SearchEngine.DUCKDUCKGO, max_results, region, safe_search
                )
            raise

    async def _search_duckduckgo(
        self,
        query: str,
        max_results: int,
        region: str,
        safe_search: str,
    ) -> List[SearchResult]:
        """Search using DuckDuckGo."""
        results = []

        # Run in thread pool since ddg-search is synchronous
        def do_search():
            with DDGS() as ddgs:
                return list(ddgs.text(
                    query,
                    region=region,
                    safesearch=safe_search,
                    max_results=max_results,
                ))

        loop = asyncio.get_event_loop()
        raw_results = await loop.run_in_executor(None, do_search)

        for i, r in enumerate(raw_results):
            results.append(SearchResult(
                title=r.get("title", ""),
                url=r.get("href", r.get("link", "")),
                snippet=r.get("body", r.get("snippet", "")),
                source="duckduckgo",
                position=i + 1,
            ))

        return results

    async def _search_brave(
        self,
        query: str,
        max_results: int,
        region: str,
    ) -> List[SearchResult]:
        """Search using Brave Search API."""
        if not self.brave_api_key:
            raise ValueError("Brave API key not configured")

        async with httpx.AsyncClient() as client:
            response = await client.get(
                "https://api.search.brave.com/res/v1/web/search",
                params={
                    "q": query,
                    "count": max_results,
                    "country": region[:2] if region != "wt-wt" else "us",
                },
                headers={
                    "X-Subscription-Token": self.brave_api_key,
                    "Accept": "application/json",
                },
                timeout=self.timeout,
            )
            response.raise_for_status()
            data = response.json()

        results = []
        for i, r in enumerate(data.get("web", {}).get("results", [])):
            results.append(SearchResult(
                title=r.get("title", ""),
                url=r.get("url", ""),
                snippet=r.get("description", ""),
                source="brave",
                position=i + 1,
                metadata={
                    "age": r.get("age"),
                    "language": r.get("language"),
                },
            ))

        return results

    async def _search_serpapi(
        self,
        query: str,
        max_results: int,
        region: str,
    ) -> List[SearchResult]:
        """Search using SerpAPI."""
        if not self.serpapi_key:
            raise ValueError("SerpAPI key not configured")

        async with httpx.AsyncClient() as client:
            response = await client.get(
                "https://serpapi.com/search.json",
                params={
                    "q": query,
                    "num": max_results,
                    "api_key": self.serpapi_key,
                    "gl": region[:2] if region != "wt-wt" else "us",
                },
                timeout=self.timeout,
            )
            response.raise_for_status()
            data = response.json()

        results = []
        for i, r in enumerate(data.get("organic_results", [])):
            results.append(SearchResult(
                title=r.get("title", ""),
                url=r.get("link", ""),
                snippet=r.get("snippet", ""),
                source="serpapi",
                position=r.get("position", i + 1),
                metadata={
                    "date": r.get("date"),
                    "cached_page_link": r.get("cached_page_link"),
                },
            ))

        return results

    async def search_news(
        self,
        query: str,
        max_results: int = 10,
        region: str = "wt-wt",
    ) -> SearchResponse:
        """Search news articles."""
        start_time = datetime.utcnow()
        results = []

        def do_search():
            with DDGS() as ddgs:
                return list(ddgs.news(
                    query,
                    region=region,
                    max_results=max_results,
                ))

        loop = asyncio.get_event_loop()
        raw_results = await loop.run_in_executor(None, do_search)

        for i, r in enumerate(raw_results):
            results.append(SearchResult(
                title=r.get("title", ""),
                url=r.get("url", r.get("link", "")),
                snippet=r.get("body", r.get("excerpt", "")),
                source="duckduckgo_news",
                position=i + 1,
                metadata={
                    "date": r.get("date"),
                    "source": r.get("source"),
                    "image": r.get("image"),
                },
            ))

        search_time = (datetime.utcnow() - start_time).total_seconds() * 1000

        return SearchResponse(
            query=query,
            engine=SearchEngine.DUCKDUCKGO,
            results=results,
            total_results=len(results),
            search_time_ms=search_time,
        )

    async def search_images(
        self,
        query: str,
        max_results: int = 10,
        region: str = "wt-wt",
        safe_search: str = "moderate",
    ) -> SearchResponse:
        """Search for images."""
        start_time = datetime.utcnow()
        results = []

        def do_search():
            with DDGS() as ddgs:
                return list(ddgs.images(
                    query,
                    region=region,
                    safesearch=safe_search,
                    max_results=max_results,
                ))

        loop = asyncio.get_event_loop()
        raw_results = await loop.run_in_executor(None, do_search)

        for i, r in enumerate(raw_results):
            results.append(SearchResult(
                title=r.get("title", ""),
                url=r.get("image", ""),
                snippet=r.get("source", ""),
                source="duckduckgo_images",
                position=i + 1,
                metadata={
                    "width": r.get("width"),
                    "height": r.get("height"),
                    "thumbnail": r.get("thumbnail"),
                    "source_url": r.get("url"),
                },
            ))

        search_time = (datetime.utcnow() - start_time).total_seconds() * 1000

        return SearchResponse(
            query=query,
            engine=SearchEngine.DUCKDUCKGO,
            results=results,
            total_results=len(results),
            search_time_ms=search_time,
        )


# Singleton instance
_web_searcher: Optional[WebSearcher] = None


def get_web_searcher() -> WebSearcher:
    """Get or create the web searcher singleton."""
    global _web_searcher
    if _web_searcher is None:
        from .config import get_settings
        settings = get_settings()
        _web_searcher = WebSearcher(
            default_engine=settings.default_search_engine,
            brave_api_key=settings.brave_api_key or None,
            serpapi_key=settings.serpapi_key or None,
            timeout=settings.search_timeout,
            max_results=settings.max_search_results,
        )
    return _web_searcher
