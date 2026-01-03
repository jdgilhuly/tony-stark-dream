"""JARVIS News Service - NewsAPI Integration."""

import logging
import hashlib
from contextlib import asynccontextmanager
from datetime import datetime, timedelta
from typing import Optional
from functools import lru_cache

from fastapi import FastAPI, HTTPException, Depends, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings
import httpx
import redis.asyncio as redis
from jose import jwt, JWTError

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class Settings(BaseSettings):
    service_name: str = "news-service"
    host: str = "0.0.0.0"
    port: int = 8004

    newsapi_key: str = ""
    newsapi_base_url: str = "https://newsapi.org/v2"

    redis_url: str = "redis://localhost:6379/0"
    cache_ttl_seconds: int = 3600  # 1 hour

    jwt_secret: str = "development-secret-change-in-production"
    jwt_algorithm: str = "HS256"

    class Config:
        env_file = ".env"


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()


# Models
class NewsSource(BaseModel):
    id: Optional[str] = None
    name: str


class NewsArticle(BaseModel):
    source: NewsSource
    author: Optional[str] = None
    title: str
    description: Optional[str] = None
    url: str
    url_to_image: Optional[str] = None
    published_at: datetime
    content: Optional[str] = None


class NewsResponse(BaseModel):
    status: str
    total_results: int
    articles: list[NewsArticle]
    cached: bool = False
    cache_timestamp: Optional[datetime] = None


class TopHeadlinesParams(BaseModel):
    country: Optional[str] = "us"
    category: Optional[str] = None
    sources: Optional[str] = None
    q: Optional[str] = None
    page_size: int = Field(default=10, ge=1, le=100)
    page: int = Field(default=1, ge=1)


# Redis
_redis: Optional[redis.Redis] = None


async def get_redis() -> redis.Redis:
    global _redis
    if _redis is None:
        _redis = redis.from_url(settings.redis_url, decode_responses=True)
    return _redis


async def get_cached(key: str) -> Optional[str]:
    try:
        r = await get_redis()
        return await r.get(key)
    except Exception as e:
        logger.warning(f"Cache read error: {e}")
        return None


async def set_cached(key: str, data: str, ttl: int = None):
    try:
        r = await get_redis()
        await r.set(key, data, ex=ttl or settings.cache_ttl_seconds)
    except Exception as e:
        logger.warning(f"Cache write error: {e}")


def cache_key(endpoint: str, **params) -> str:
    param_str = "&".join(f"{k}={v}" for k, v in sorted(params.items()) if v)
    return f"news:{endpoint}:{hashlib.md5(param_str.encode()).hexdigest()}"


# Auth
async def get_current_user(request: Request) -> dict:
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing authorization token")

    token = auth_header.split(" ")[1]
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
        return {"user_id": payload.get("userId")}
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info(f"Starting {settings.service_name}")
    yield
    if _redis:
        await _redis.close()
    logger.info(f"Shutting down {settings.service_name}")


app = FastAPI(
    title="JARVIS News Service",
    description="News aggregation from NewsAPI with caching",
    version="0.1.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Available categories for NewsAPI
NEWS_CATEGORIES = [
    "business", "entertainment", "general", "health",
    "science", "sports", "technology"
]


@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "service": settings.service_name,
        "timestamp": datetime.utcnow().isoformat()
    }


@app.get("/categories")
async def get_categories():
    """List available news categories."""
    return {"categories": NEWS_CATEGORIES}


@app.get("/headlines", response_model=NewsResponse)
async def get_top_headlines(
    country: str = Query("us", min_length=2, max_length=2),
    category: Optional[str] = Query(None, regex=f"^({'|'.join(NEWS_CATEGORIES)})$"),
    sources: Optional[str] = None,
    q: Optional[str] = None,
    page_size: int = Query(10, ge=1, le=100),
    page: int = Query(1, ge=1),
    user: dict = Depends(get_current_user)
):
    """Get top news headlines."""
    import json

    # Check cache
    key = cache_key("headlines", country=country, category=category, sources=sources, q=q, page_size=page_size, page=page)
    cached_data = await get_cached(key)

    if cached_data:
        data = json.loads(cached_data)
        data["cached"] = True
        return NewsResponse(**data)

    if not settings.newsapi_key:
        raise HTTPException(status_code=503, detail="News API not configured")

    params = {
        "apiKey": settings.newsapi_key,
        "pageSize": page_size,
        "page": page
    }

    # Note: sources cannot be mixed with country or category
    if sources:
        params["sources"] = sources
    else:
        params["country"] = country
        if category:
            params["category"] = category

    if q:
        params["q"] = q

    async with httpx.AsyncClient() as client:
        resp = await client.get(f"{settings.newsapi_base_url}/top-headlines", params=params)

        if resp.status_code != 200:
            logger.error(f"NewsAPI error: {resp.text}")
            raise HTTPException(status_code=502, detail="News API error")

        data = resp.json()

    if data.get("status") != "ok":
        raise HTTPException(status_code=502, detail=data.get("message", "News API error"))

    articles = []
    for article in data.get("articles", []):
        try:
            articles.append(NewsArticle(
                source=NewsSource(
                    id=article.get("source", {}).get("id"),
                    name=article.get("source", {}).get("name", "Unknown")
                ),
                author=article.get("author"),
                title=article.get("title", ""),
                description=article.get("description"),
                url=article.get("url", ""),
                url_to_image=article.get("urlToImage"),
                published_at=datetime.fromisoformat(article["publishedAt"].replace("Z", "+00:00")),
                content=article.get("content")
            ))
        except Exception as e:
            logger.warning(f"Failed to parse article: {e}")
            continue

    response = NewsResponse(
        status="ok",
        total_results=data.get("totalResults", len(articles)),
        articles=articles,
        cached=False,
        cache_timestamp=datetime.utcnow()
    )

    # Cache the response
    await set_cached(key, response.model_dump_json())

    return response


@app.get("/search", response_model=NewsResponse)
async def search_news(
    q: str = Query(..., min_length=1, description="Search query"),
    sources: Optional[str] = None,
    from_date: Optional[datetime] = None,
    to_date: Optional[datetime] = None,
    language: str = Query("en", min_length=2, max_length=2),
    sort_by: str = Query("publishedAt", regex="^(relevancy|popularity|publishedAt)$"),
    page_size: int = Query(10, ge=1, le=100),
    page: int = Query(1, ge=1),
    user: dict = Depends(get_current_user)
):
    """Search for news articles."""
    import json

    # Default date range: last 7 days
    if not from_date:
        from_date = datetime.utcnow() - timedelta(days=7)
    if not to_date:
        to_date = datetime.utcnow()

    key = cache_key("search", q=q, sources=sources, from_date=from_date.isoformat(), to_date=to_date.isoformat(), language=language, sort_by=sort_by, page_size=page_size, page=page)
    cached_data = await get_cached(key)

    if cached_data:
        data = json.loads(cached_data)
        data["cached"] = True
        return NewsResponse(**data)

    if not settings.newsapi_key:
        raise HTTPException(status_code=503, detail="News API not configured")

    params = {
        "apiKey": settings.newsapi_key,
        "q": q,
        "from": from_date.strftime("%Y-%m-%d"),
        "to": to_date.strftime("%Y-%m-%d"),
        "language": language,
        "sortBy": sort_by,
        "pageSize": page_size,
        "page": page
    }

    if sources:
        params["sources"] = sources

    async with httpx.AsyncClient() as client:
        resp = await client.get(f"{settings.newsapi_base_url}/everything", params=params)

        if resp.status_code != 200:
            logger.error(f"NewsAPI error: {resp.text}")
            raise HTTPException(status_code=502, detail="News API error")

        data = resp.json()

    if data.get("status") != "ok":
        raise HTTPException(status_code=502, detail=data.get("message", "News API error"))

    articles = []
    for article in data.get("articles", []):
        try:
            articles.append(NewsArticle(
                source=NewsSource(
                    id=article.get("source", {}).get("id"),
                    name=article.get("source", {}).get("name", "Unknown")
                ),
                author=article.get("author"),
                title=article.get("title", ""),
                description=article.get("description"),
                url=article.get("url", ""),
                url_to_image=article.get("urlToImage"),
                published_at=datetime.fromisoformat(article["publishedAt"].replace("Z", "+00:00")),
                content=article.get("content")
            ))
        except Exception as e:
            logger.warning(f"Failed to parse article: {e}")
            continue

    response = NewsResponse(
        status="ok",
        total_results=data.get("totalResults", len(articles)),
        articles=articles,
        cached=False,
        cache_timestamp=datetime.utcnow()
    )

    await set_cached(key, response.model_dump_json())

    return response


@app.get("/personalized", response_model=NewsResponse)
async def get_personalized_news(
    categories: str = Query("technology,business", description="Comma-separated categories"),
    page_size: int = Query(10, ge=1, le=100),
    user: dict = Depends(get_current_user)
):
    """Get personalized news based on user preferences."""
    category_list = [c.strip() for c in categories.split(",") if c.strip() in NEWS_CATEGORIES]

    if not category_list:
        category_list = ["technology", "business"]

    all_articles = []
    per_category = max(1, page_size // len(category_list))

    for category in category_list:
        try:
            resp = await get_top_headlines(
                country="us",
                category=category,
                page_size=per_category,
                page=1,
                user=user
            )
            all_articles.extend(resp.articles)
        except Exception as e:
            logger.warning(f"Failed to get {category} news: {e}")

    # Sort by published date
    all_articles.sort(key=lambda x: x.published_at, reverse=True)

    return NewsResponse(
        status="ok",
        total_results=len(all_articles),
        articles=all_articles[:page_size],
        cached=False,
        cache_timestamp=datetime.utcnow()
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host=settings.host, port=settings.port, reload=True)
