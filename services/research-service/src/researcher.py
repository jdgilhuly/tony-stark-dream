"""
Research Module

Combines search, extraction, and synthesis for comprehensive research.
"""

import asyncio
import hashlib
import json
import logging
import sqlite3
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

from diskcache import Cache

from .search import WebSearcher, SearchResult, SearchResponse, get_web_searcher
from .extractor import ContentExtractor, ExtractedContent, get_content_extractor

logger = logging.getLogger(__name__)


@dataclass
class Source:
    """A research source."""
    url: str
    title: str
    snippet: str
    content: Optional[str] = None
    relevance_score: float = 0.0
    extracted_at: Optional[str] = None


@dataclass
class ResearchResult:
    """Result of a research query."""
    query: str
    summary: str
    sources: List[Source]
    key_points: List[str]
    related_queries: List[str]
    total_sources: int
    research_time_ms: float
    cached: bool = False


@dataclass
class KnowledgeEntry:
    """An entry in the knowledge base."""
    id: str
    topic: str
    content: str
    sources: List[str]
    created_at: str
    updated_at: str
    access_count: int = 0


class ResearchCache:
    """Cache for research results."""

    def __init__(self, cache_dir: str, ttl_seconds: int = 3600):
        self.cache = Cache(cache_dir)
        self.ttl_seconds = ttl_seconds

    def get(self, key: str) -> Optional[Dict[str, Any]]:
        """Get cached result."""
        return self.cache.get(key)

    def set(self, key: str, value: Dict[str, Any]) -> None:
        """Cache a result."""
        self.cache.set(key, value, expire=self.ttl_seconds)

    def make_key(self, query: str, **kwargs) -> str:
        """Generate cache key."""
        data = {"query": query, **kwargs}
        return hashlib.md5(json.dumps(data, sort_keys=True).encode()).hexdigest()

    def close(self) -> None:
        """Close the cache."""
        self.cache.close()


class KnowledgeBase:
    """SQLite-based knowledge base for storing research findings."""

    def __init__(self, db_path: str):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _init_db(self) -> None:
        """Initialize the database schema."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS knowledge (
                    id TEXT PRIMARY KEY,
                    topic TEXT NOT NULL,
                    content TEXT NOT NULL,
                    sources TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    access_count INTEGER DEFAULT 0
                )
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_topic ON knowledge(topic)
            """)
            conn.execute("""
                CREATE VIRTUAL TABLE IF NOT EXISTS knowledge_fts
                USING fts5(topic, content, content='knowledge', content_rowid='rowid')
            """)

    def store(self, entry: KnowledgeEntry) -> None:
        """Store a knowledge entry."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT OR REPLACE INTO knowledge
                (id, topic, content, sources, created_at, updated_at, access_count)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                entry.id,
                entry.topic,
                entry.content,
                json.dumps(entry.sources),
                entry.created_at,
                entry.updated_at,
                entry.access_count,
            ))

    def get(self, entry_id: str) -> Optional[KnowledgeEntry]:
        """Get a knowledge entry by ID."""
        with sqlite3.connect(self.db_path) as conn:
            row = conn.execute(
                "SELECT * FROM knowledge WHERE id = ?", (entry_id,)
            ).fetchone()

            if row:
                self._increment_access(entry_id)
                return KnowledgeEntry(
                    id=row[0],
                    topic=row[1],
                    content=row[2],
                    sources=json.loads(row[3]),
                    created_at=row[4],
                    updated_at=row[5],
                    access_count=row[6] + 1,
                )
            return None

    def search(self, query: str, limit: int = 10) -> List[KnowledgeEntry]:
        """Search knowledge base."""
        with sqlite3.connect(self.db_path) as conn:
            rows = conn.execute("""
                SELECT k.* FROM knowledge k
                JOIN knowledge_fts fts ON k.rowid = fts.rowid
                WHERE knowledge_fts MATCH ?
                ORDER BY rank
                LIMIT ?
            """, (query, limit)).fetchall()

            return [
                KnowledgeEntry(
                    id=row[0],
                    topic=row[1],
                    content=row[2],
                    sources=json.loads(row[3]),
                    created_at=row[4],
                    updated_at=row[5],
                    access_count=row[6],
                )
                for row in rows
            ]

    def _increment_access(self, entry_id: str) -> None:
        """Increment access count."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "UPDATE knowledge SET access_count = access_count + 1 WHERE id = ?",
                (entry_id,)
            )


class Researcher:
    """
    Research assistant that combines search, extraction, and synthesis.

    Features:
    - Multi-source search
    - Content extraction and parsing
    - Result caching
    - Knowledge base building
    """

    def __init__(
        self,
        searcher: Optional[WebSearcher] = None,
        extractor: Optional[ContentExtractor] = None,
        cache_dir: str = "./data/research_cache",
        cache_ttl: int = 3600,
        knowledge_db_path: str = "./data/knowledge.db",
        enable_knowledge_base: bool = True,
    ):
        self.searcher = searcher or get_web_searcher()
        self.extractor = extractor or get_content_extractor()
        self.cache = ResearchCache(cache_dir, cache_ttl)
        self.enable_knowledge_base = enable_knowledge_base

        if enable_knowledge_base:
            self.knowledge_base = KnowledgeBase(knowledge_db_path)
        else:
            self.knowledge_base = None

    async def research(
        self,
        query: str,
        max_sources: int = 5,
        extract_content: bool = True,
        use_cache: bool = True,
    ) -> ResearchResult:
        """
        Conduct research on a topic.

        Args:
            query: Research query
            max_sources: Maximum sources to include
            extract_content: Whether to extract full content
            use_cache: Whether to use cached results

        Returns:
            ResearchResult with summary, sources, and key points
        """
        start_time = datetime.utcnow()

        # Check cache
        cache_key = self.cache.make_key(query, max_sources=max_sources)
        if use_cache:
            cached = self.cache.get(cache_key)
            if cached:
                logger.info(f"Cache hit for query: {query}")
                return ResearchResult(**cached, cached=True)

        # Search
        search_response = await self.searcher.search(query, max_results=max_sources * 2)

        # Extract content from top results
        sources = []
        urls_to_extract = [r.url for r in search_response.results[:max_sources]]

        if extract_content:
            extracted = await self.extractor.extract_multiple(
                urls_to_extract, max_concurrent=3
            )
            content_map = {e.url: e for e in extracted}
        else:
            content_map = {}

        for result in search_response.results[:max_sources]:
            extracted = content_map.get(result.url)
            sources.append(Source(
                url=result.url,
                title=result.title,
                snippet=result.snippet,
                content=extracted.text[:2000] if extracted else None,
                relevance_score=1.0 - (result.position / len(search_response.results)),
                extracted_at=datetime.utcnow().isoformat() if extracted else None,
            ))

        # Generate summary and key points from extracted content
        summary, key_points = self._synthesize(query, sources)

        # Generate related queries
        related_queries = self._generate_related_queries(query, sources)

        research_time = (datetime.utcnow() - start_time).total_seconds() * 1000

        result = ResearchResult(
            query=query,
            summary=summary,
            sources=sources,
            key_points=key_points,
            related_queries=related_queries,
            total_sources=len(sources),
            research_time_ms=research_time,
        )

        # Cache result
        if use_cache:
            self.cache.set(cache_key, {
                "query": result.query,
                "summary": result.summary,
                "sources": [
                    {
                        "url": s.url,
                        "title": s.title,
                        "snippet": s.snippet,
                        "content": s.content,
                        "relevance_score": s.relevance_score,
                        "extracted_at": s.extracted_at,
                    }
                    for s in result.sources
                ],
                "key_points": result.key_points,
                "related_queries": result.related_queries,
                "total_sources": result.total_sources,
                "research_time_ms": result.research_time_ms,
            })

        return result

    def _synthesize(self, query: str, sources: List[Source]) -> tuple:
        """Synthesize summary and key points from sources."""
        # Simple synthesis - in production, this would use an LLM
        all_content = []
        for source in sources:
            if source.content:
                all_content.append(source.content)
            else:
                all_content.append(source.snippet)

        combined = "\n\n".join(all_content)

        # Extract first paragraph as summary
        paragraphs = combined.split("\n\n")
        summary = paragraphs[0] if paragraphs else "No summary available."

        # Extract potential key points (sentences starting with key indicators)
        key_points = []
        sentences = combined.replace("\n", " ").split(". ")
        for sentence in sentences[:20]:
            sentence = sentence.strip()
            if len(sentence) > 30 and len(sentence) < 200:
                # Simple heuristic for important sentences
                lower = sentence.lower()
                if any(word in lower for word in [
                    "important", "key", "main", "significant",
                    "research shows", "studies", "according to",
                    "first", "second", "finally", "therefore"
                ]):
                    key_points.append(sentence + ".")
                    if len(key_points) >= 5:
                        break

        if not key_points and sources:
            # Fallback to snippets
            key_points = [s.snippet for s in sources[:3] if s.snippet]

        return summary[:500], key_points[:5]

    def _generate_related_queries(self, query: str, sources: List[Source]) -> List[str]:
        """Generate related search queries."""
        # Simple related query generation
        words = query.lower().split()
        related = []

        # Add question variants
        if not query.startswith(("what", "how", "why", "when", "where")):
            related.append(f"what is {query}")
            related.append(f"how does {query} work")

        # Add "best" and "examples" variants
        if len(words) <= 3:
            related.append(f"best {query}")
            related.append(f"{query} examples")

        return related[:5]

    async def quick_answer(self, question: str) -> Dict[str, Any]:
        """Get a quick answer to a question."""
        search_response = await self.searcher.search(question, max_results=3)

        if not search_response.results:
            return {"answer": None, "source": None}

        # Use the first result's snippet as the answer
        first = search_response.results[0]
        return {
            "answer": first.snippet,
            "source": {
                "title": first.title,
                "url": first.url,
            },
        }

    async def search_news(
        self,
        query: str,
        max_results: int = 10,
    ) -> SearchResponse:
        """Search for news articles."""
        return await self.searcher.search_news(query, max_results)

    def store_knowledge(
        self,
        topic: str,
        content: str,
        sources: List[str],
    ) -> str:
        """Store knowledge in the knowledge base."""
        if not self.knowledge_base:
            raise ValueError("Knowledge base not enabled")

        entry_id = hashlib.md5(f"{topic}:{content[:100]}".encode()).hexdigest()[:16]
        now = datetime.utcnow().isoformat()

        entry = KnowledgeEntry(
            id=entry_id,
            topic=topic,
            content=content,
            sources=sources,
            created_at=now,
            updated_at=now,
        )

        self.knowledge_base.store(entry)
        return entry_id

    def search_knowledge(self, query: str, limit: int = 10) -> List[KnowledgeEntry]:
        """Search the knowledge base."""
        if not self.knowledge_base:
            return []
        return self.knowledge_base.search(query, limit)


# Singleton instance
_researcher: Optional[Researcher] = None


def get_researcher() -> Researcher:
    """Get or create the researcher singleton."""
    global _researcher
    if _researcher is None:
        from .config import get_settings
        settings = get_settings()
        _researcher = Researcher(
            cache_dir=settings.cache_dir,
            cache_ttl=settings.cache_ttl_seconds,
            knowledge_db_path=settings.knowledge_db_path,
            enable_knowledge_base=settings.enable_knowledge_base,
        )
    return _researcher
