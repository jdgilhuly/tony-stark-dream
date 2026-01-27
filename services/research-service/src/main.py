"""
JARVIS Research Service - Main FastAPI Application

Provides web search, content extraction, and research synthesis.
"""

import logging
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, HTTPException, Depends, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from jose import jwt, JWTError

from .config import get_settings
from .search import get_web_searcher, SearchEngine, SearchResult, SearchResponse
from .extractor import get_content_extractor, ExtractedContent
from .researcher import get_researcher, ResearchResult, Source, KnowledgeEntry

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler."""
    logger.info(f"Starting {settings.service_name}")
    # Initialize services
    get_web_searcher()
    get_content_extractor()
    get_researcher()
    yield
    logger.info(f"Shutting down {settings.service_name}")


app = FastAPI(
    title="JARVIS Research Service",
    description="Web search, content extraction, and research synthesis",
    version="0.1.0",
    lifespan=lifespan
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Request/Response Models
class SearchRequest(BaseModel):
    query: str
    engine: Optional[str] = None  # duckduckgo, brave, serpapi
    max_results: int = 10
    region: str = "wt-wt"
    safe_search: str = "moderate"


class SearchResultModel(BaseModel):
    title: str
    url: str
    snippet: str
    source: str
    position: int
    metadata: Dict[str, Any] = {}


class SearchResponseModel(BaseModel):
    query: str
    engine: str
    results: List[SearchResultModel]
    total_results: int
    search_time_ms: float


class ExtractRequest(BaseModel):
    url: str
    include_html: bool = False
    include_links: bool = True
    include_images: bool = True


class ExtractedContentModel(BaseModel):
    url: str
    title: str
    text: str
    markdown: str
    author: Optional[str]
    publish_date: Optional[str]
    description: Optional[str]
    language: Optional[str]
    domain: str
    word_count: int
    links: List[Dict[str, str]]
    images: List[Dict[str, str]]
    extraction_time_ms: float


class ResearchRequest(BaseModel):
    query: str
    max_sources: int = 5
    extract_content: bool = True
    use_cache: bool = True


class SourceModel(BaseModel):
    url: str
    title: str
    snippet: str
    content: Optional[str]
    relevance_score: float
    extracted_at: Optional[str]


class ResearchResponseModel(BaseModel):
    query: str
    summary: str
    sources: List[SourceModel]
    key_points: List[str]
    related_queries: List[str]
    total_sources: int
    research_time_ms: float
    cached: bool


class KnowledgeRequest(BaseModel):
    topic: str
    content: str
    sources: List[str] = []


class KnowledgeEntryModel(BaseModel):
    id: str
    topic: str
    content: str
    sources: List[str]
    created_at: str
    updated_at: str
    access_count: int


# Auth dependency
async def get_current_user(request: Request) -> dict:
    """Extract user from JWT token."""
    auth_header = request.headers.get("Authorization")

    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing authorization token")

    token = auth_header.split(" ")[1]

    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret,
            algorithms=[settings.jwt_algorithm]
        )
        return {"user_id": payload.get("userId")}
    except JWTError as e:
        logger.error(f"JWT decode error: {e}")
        raise HTTPException(status_code=401, detail="Invalid token")


# Health check
@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": settings.service_name,
        "timestamp": datetime.utcnow().isoformat(),
        "search_engine": settings.default_search_engine,
    }


# Search endpoints
@app.post("/search", response_model=SearchResponseModel)
async def search(
    request: SearchRequest,
    user: dict = Depends(get_current_user),
):
    """Search the web."""
    try:
        searcher = get_web_searcher()

        engine = None
        if request.engine:
            try:
                engine = SearchEngine(request.engine)
            except ValueError:
                pass

        response = await searcher.search(
            query=request.query,
            engine=engine,
            max_results=request.max_results,
            region=request.region,
            safe_search=request.safe_search,
        )

        return SearchResponseModel(
            query=response.query,
            engine=response.engine.value,
            results=[
                SearchResultModel(
                    title=r.title,
                    url=r.url,
                    snippet=r.snippet,
                    source=r.source,
                    position=r.position,
                    metadata=r.metadata,
                )
                for r in response.results
            ],
            total_results=response.total_results,
            search_time_ms=response.search_time_ms,
        )

    except Exception as e:
        logger.error(f"Search error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/search/news", response_model=SearchResponseModel)
async def search_news(
    query: str,
    max_results: int = 10,
    user: dict = Depends(get_current_user),
):
    """Search news articles."""
    try:
        searcher = get_web_searcher()
        response = await searcher.search_news(query, max_results)

        return SearchResponseModel(
            query=response.query,
            engine=response.engine.value,
            results=[
                SearchResultModel(
                    title=r.title,
                    url=r.url,
                    snippet=r.snippet,
                    source=r.source,
                    position=r.position,
                    metadata=r.metadata,
                )
                for r in response.results
            ],
            total_results=response.total_results,
            search_time_ms=response.search_time_ms,
        )

    except Exception as e:
        logger.error(f"News search error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/search/images", response_model=SearchResponseModel)
async def search_images(
    query: str,
    max_results: int = 10,
    safe_search: str = "moderate",
    user: dict = Depends(get_current_user),
):
    """Search for images."""
    try:
        searcher = get_web_searcher()
        response = await searcher.search_images(query, max_results, safe_search=safe_search)

        return SearchResponseModel(
            query=response.query,
            engine=response.engine.value,
            results=[
                SearchResultModel(
                    title=r.title,
                    url=r.url,
                    snippet=r.snippet,
                    source=r.source,
                    position=r.position,
                    metadata=r.metadata,
                )
                for r in response.results
            ],
            total_results=response.total_results,
            search_time_ms=response.search_time_ms,
        )

    except Exception as e:
        logger.error(f"Image search error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Content extraction endpoints
@app.post("/extract", response_model=ExtractedContentModel)
async def extract_content(
    request: ExtractRequest,
    user: dict = Depends(get_current_user),
):
    """Extract content from a URL."""
    try:
        extractor = get_content_extractor()
        content = await extractor.extract(
            url=request.url,
            include_html=request.include_html,
            include_links=request.include_links,
            include_images=request.include_images,
        )

        return ExtractedContentModel(
            url=content.url,
            title=content.title,
            text=content.text,
            markdown=content.markdown,
            author=content.author,
            publish_date=content.publish_date,
            description=content.description,
            language=content.language,
            domain=content.domain,
            word_count=content.word_count,
            links=content.links,
            images=content.images,
            extraction_time_ms=content.extraction_time_ms,
        )

    except Exception as e:
        logger.error(f"Extraction error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/extract/batch")
async def extract_batch(
    urls: List[str],
    max_concurrent: int = 5,
    user: dict = Depends(get_current_user),
):
    """Extract content from multiple URLs."""
    try:
        extractor = get_content_extractor()
        results = await extractor.extract_multiple(urls, max_concurrent)

        return {
            "results": [
                {
                    "url": r.url,
                    "title": r.title,
                    "text": r.text[:1000],
                    "word_count": r.word_count,
                }
                for r in results
            ],
            "total": len(results),
            "failed": len(urls) - len(results),
        }

    except Exception as e:
        logger.error(f"Batch extraction error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Research endpoints
@app.post("/research", response_model=ResearchResponseModel)
async def conduct_research(
    request: ResearchRequest,
    user: dict = Depends(get_current_user),
):
    """Conduct comprehensive research on a topic."""
    try:
        researcher = get_researcher()
        result = await researcher.research(
            query=request.query,
            max_sources=request.max_sources,
            extract_content=request.extract_content,
            use_cache=request.use_cache,
        )

        return ResearchResponseModel(
            query=result.query,
            summary=result.summary,
            sources=[
                SourceModel(
                    url=s.url,
                    title=s.title,
                    snippet=s.snippet,
                    content=s.content,
                    relevance_score=s.relevance_score,
                    extracted_at=s.extracted_at,
                )
                for s in result.sources
            ],
            key_points=result.key_points,
            related_queries=result.related_queries,
            total_sources=result.total_sources,
            research_time_ms=result.research_time_ms,
            cached=result.cached,
        )

    except Exception as e:
        logger.error(f"Research error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/answer")
async def quick_answer(
    question: str,
    user: dict = Depends(get_current_user),
):
    """Get a quick answer to a question."""
    try:
        researcher = get_researcher()
        result = await researcher.quick_answer(question)
        return result

    except Exception as e:
        logger.error(f"Quick answer error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Knowledge base endpoints
@app.post("/knowledge")
async def store_knowledge(
    request: KnowledgeRequest,
    user: dict = Depends(get_current_user),
):
    """Store knowledge in the knowledge base."""
    try:
        researcher = get_researcher()
        entry_id = researcher.store_knowledge(
            topic=request.topic,
            content=request.content,
            sources=request.sources,
        )
        return {"id": entry_id, "status": "stored"}

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Knowledge storage error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/knowledge/search", response_model=List[KnowledgeEntryModel])
async def search_knowledge(
    query: str,
    limit: int = 10,
    user: dict = Depends(get_current_user),
):
    """Search the knowledge base."""
    try:
        researcher = get_researcher()
        entries = researcher.search_knowledge(query, limit)

        return [
            KnowledgeEntryModel(
                id=e.id,
                topic=e.topic,
                content=e.content,
                sources=e.sources,
                created_at=e.created_at,
                updated_at=e.updated_at,
                access_count=e.access_count,
            )
            for e in entries
        ]

    except Exception as e:
        logger.error(f"Knowledge search error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Convenience endpoints
@app.get("/lookup")
async def lookup(
    query: str,
    user: dict = Depends(get_current_user),
):
    """
    Quick lookup - searches web and returns top result with content.
    """
    try:
        searcher = get_web_searcher()
        extractor = get_content_extractor()

        # Search
        search_result = await searcher.search(query, max_results=1)

        if not search_result.results:
            return {"found": False, "query": query}

        # Extract content from top result
        top = search_result.results[0]
        try:
            content = await extractor.extract(top.url)
            return {
                "found": True,
                "query": query,
                "title": top.title,
                "url": top.url,
                "snippet": top.snippet,
                "content": content.text[:2000],
                "word_count": content.word_count,
            }
        except Exception:
            return {
                "found": True,
                "query": query,
                "title": top.title,
                "url": top.url,
                "snippet": top.snippet,
            }

    except Exception as e:
        logger.error(f"Lookup error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug
    )
