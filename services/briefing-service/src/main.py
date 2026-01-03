"""JARVIS Briefing Service - Daily briefing aggregation and LLM summarization."""

import logging
import json
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timedelta
from typing import Optional
from functools import lru_cache

from fastapi import FastAPI, HTTPException, Depends, Query, Request, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings
import httpx
import redis.asyncio as redis
import boto3
from botocore.config import Config
from jose import jwt, JWTError
from apscheduler.schedulers.asyncio import AsyncIOScheduler

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class Settings(BaseSettings):
    service_name: str = "briefing-service"
    host: str = "0.0.0.0"
    port: int = 8005

    # Service URLs
    weather_service_url: str = "http://localhost:8003"
    news_service_url: str = "http://localhost:8004"
    calendar_service_url: str = "http://localhost:8006"

    # AWS Bedrock
    aws_region: str = "us-east-1"
    aws_access_key_id: str | None = None
    aws_secret_access_key: str | None = None
    bedrock_model_id: str = "anthropic.claude-3-5-sonnet-20241022-v2:0"

    # Redis & DynamoDB
    redis_url: str = "redis://localhost:6379/0"
    dynamodb_table: str = "jarvis-briefings"

    # JWT
    jwt_secret: str = "development-secret-change-in-production"
    jwt_algorithm: str = "HS256"

    class Config:
        env_file = ".env"


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()


# Models
class WeatherSummary(BaseModel):
    location: str
    temperature: float
    condition: str
    high: float
    low: float
    humidity: int
    wind_speed: float


class NewsHeadline(BaseModel):
    title: str
    source: str
    category: str
    url: str


class CalendarEvent(BaseModel):
    title: str
    start_time: datetime
    end_time: Optional[datetime] = None
    location: Optional[str] = None
    is_all_day: bool = False


class TaskItem(BaseModel):
    title: str
    due_date: Optional[datetime] = None
    priority: str = "medium"
    status: str = "pending"


class DailyBriefing(BaseModel):
    id: str
    user_id: str
    generated_at: datetime
    greeting: str
    summary: str
    weather: Optional[WeatherSummary] = None
    news: list[NewsHeadline] = []
    calendar: list[CalendarEvent] = []
    tasks: list[TaskItem] = []
    audio_url: Optional[str] = None


class BriefingRequest(BaseModel):
    location_lat: Optional[float] = None
    location_lon: Optional[float] = None
    city: Optional[str] = None
    news_categories: list[str] = ["technology", "business"]
    include_calendar: bool = True
    include_tasks: bool = True


# Redis
_redis: Optional[redis.Redis] = None


async def get_redis() -> redis.Redis:
    global _redis
    if _redis is None:
        _redis = redis.from_url(settings.redis_url, decode_responses=True)
    return _redis


# Bedrock client
def get_bedrock_client():
    config = Config(
        region_name=settings.aws_region,
        retries={"max_attempts": 3, "mode": "adaptive"}
    )
    return boto3.client(
        "bedrock-runtime",
        config=config,
        aws_access_key_id=settings.aws_access_key_id,
        aws_secret_access_key=settings.aws_secret_access_key,
    )


# Auth
async def get_current_user(request: Request) -> dict:
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing authorization token")

    token = auth_header.split(" ")[1]
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
        return {
            "user_id": payload.get("userId"),
            "preferred_title": payload.get("preferredTitle", "sir"),
            "timezone": payload.get("timezone", "UTC")
        }
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")


# Scheduler for scheduled briefings
scheduler = AsyncIOScheduler()


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info(f"Starting {settings.service_name}")
    scheduler.start()
    yield
    scheduler.shutdown()
    if _redis:
        await _redis.close()
    logger.info(f"Shutting down {settings.service_name}")


app = FastAPI(
    title="JARVIS Briefing Service",
    description="Daily briefing aggregation with LLM summarization",
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


async def fetch_weather(lat: float, lon: float, token: str) -> Optional[dict]:
    """Fetch weather data from weather service."""
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(
                f"{settings.weather_service_url}/weather",
                params={"lat": lat, "lon": lon, "units": "imperial"},
                headers={"Authorization": f"Bearer {token}"}
            )
            if resp.status_code == 200:
                return resp.json()
    except Exception as e:
        logger.warning(f"Weather fetch failed: {e}")
    return None


async def fetch_news(categories: list[str], token: str) -> list[dict]:
    """Fetch news from news service."""
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(
                f"{settings.news_service_url}/personalized",
                params={"categories": ",".join(categories), "page_size": 5},
                headers={"Authorization": f"Bearer {token}"}
            )
            if resp.status_code == 200:
                data = resp.json()
                return data.get("articles", [])
    except Exception as e:
        logger.warning(f"News fetch failed: {e}")
    return []


async def generate_briefing_summary(
    weather: Optional[dict],
    news: list[dict],
    calendar: list[dict],
    tasks: list[dict],
    preferred_title: str,
    current_time: datetime
) -> tuple[str, str]:
    """Generate briefing greeting and summary using Bedrock."""

    # Build context
    context_parts = []

    greeting_time = "Good morning" if current_time.hour < 12 else ("Good afternoon" if current_time.hour < 18 else "Good evening")

    if weather:
        current = weather.get("current", {})
        context_parts.append(f"Weather: {current.get('temperature', 'N/A')}°F, {current.get('condition', 'Unknown')}")

    if calendar:
        events = [f"- {e.get('title')} at {e.get('start_time')}" for e in calendar[:3]]
        context_parts.append(f"Today's events:\n" + "\n".join(events))

    if tasks:
        pending = [t for t in tasks if t.get("status") != "completed"][:3]
        if pending:
            task_list = [f"- {t.get('title')} ({t.get('priority')})" for t in pending]
            context_parts.append(f"Pending tasks:\n" + "\n".join(task_list))

    if news:
        headlines = [f"- {n.get('title', 'No title')}" for n in news[:3]]
        context_parts.append(f"Top news:\n" + "\n".join(headlines))

    context = "\n\n".join(context_parts)

    prompt = f"""You are JARVIS, a sophisticated AI assistant with a refined British butler demeanor.
Generate a brief, personalized morning briefing for your user whom you address as "{preferred_title}".

Current time: {current_time.strftime("%A, %B %d, %Y at %I:%M %p")}

Today's information:
{context}

Generate a concise briefing (2-3 paragraphs) that:
1. Starts with an appropriate greeting
2. Summarizes the weather and any notable conditions
3. Mentions key calendar events or meetings
4. Highlights important news if relevant
5. Reminds about priority tasks

Use your characteristic JARVIS personality - professional, helpful, with subtle dry wit."""

    try:
        bedrock = get_bedrock_client()
        response = bedrock.invoke_model(
            modelId=settings.bedrock_model_id,
            body=json.dumps({
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": 500,
                "messages": [{"role": "user", "content": prompt}]
            }),
            contentType="application/json",
            accept="application/json"
        )

        response_body = json.loads(response["body"].read())
        content = response_body.get("content", [])
        summary = content[0].get("text", "") if content else ""

        greeting = f"{greeting_time}, {preferred_title}."
        return greeting, summary

    except Exception as e:
        logger.error(f"Bedrock summarization error: {e}")
        # Fallback greeting
        greeting = f"{greeting_time}, {preferred_title}."
        summary = f"I have your briefing ready. " + context_parts[0] if context_parts else "Your briefing is ready."
        return greeting, summary


@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "service": settings.service_name,
        "timestamp": datetime.utcnow().isoformat()
    }


@app.post("/briefing/generate", response_model=DailyBriefing)
async def generate_briefing(
    request: BriefingRequest,
    background_tasks: BackgroundTasks,
    user: dict = Depends(get_current_user),
    req: Request = None
):
    """Generate a new daily briefing."""
    token = req.headers.get("Authorization", "").replace("Bearer ", "")
    user_id = user["user_id"]
    preferred_title = user["preferred_title"]
    current_time = datetime.utcnow()

    # Fetch data from services
    weather_data = None
    if request.location_lat and request.location_lon:
        weather_data = await fetch_weather(request.location_lat, request.location_lon, token)

    news_data = await fetch_news(request.news_categories, token)

    # Calendar and tasks would come from calendar service
    calendar_data = []
    tasks_data = []

    # Generate summary with LLM
    greeting, summary = await generate_briefing_summary(
        weather=weather_data,
        news=news_data,
        calendar=calendar_data,
        tasks=tasks_data,
        preferred_title=preferred_title,
        current_time=current_time
    )

    # Build response
    weather_summary = None
    if weather_data:
        current = weather_data.get("current", {})
        daily = weather_data.get("daily_forecast", [{}])
        today = daily[0] if daily else {}
        weather_summary = WeatherSummary(
            location=weather_data.get("location", "Unknown"),
            temperature=current.get("temperature", 0),
            condition=current.get("condition", "Unknown"),
            high=today.get("temp_max", current.get("temperature", 0)),
            low=today.get("temp_min", current.get("temperature", 0)),
            humidity=current.get("humidity", 0),
            wind_speed=current.get("wind_speed", 0)
        )

    news_headlines = [
        NewsHeadline(
            title=n.get("title", ""),
            source=n.get("source", {}).get("name", "Unknown"),
            category="general",
            url=n.get("url", "")
        )
        for n in news_data[:5]
    ]

    briefing = DailyBriefing(
        id=str(uuid.uuid4()),
        user_id=user_id,
        generated_at=current_time,
        greeting=greeting,
        summary=summary,
        weather=weather_summary,
        news=news_headlines,
        calendar=[],
        tasks=[]
    )

    # Cache the briefing
    try:
        r = await get_redis()
        await r.set(
            f"briefing:{user_id}:latest",
            briefing.model_dump_json(),
            ex=86400  # 24 hours
        )
    except Exception as e:
        logger.warning(f"Failed to cache briefing: {e}")

    return briefing


@app.get("/briefing/latest", response_model=Optional[DailyBriefing])
async def get_latest_briefing(user: dict = Depends(get_current_user)):
    """Get the most recent briefing for the user."""
    try:
        r = await get_redis()
        data = await r.get(f"briefing:{user['user_id']}:latest")
        if data:
            return DailyBriefing.model_validate_json(data)
    except Exception as e:
        logger.warning(f"Failed to get cached briefing: {e}")

    raise HTTPException(status_code=404, detail="No briefing available")


@app.get("/briefing/{briefing_id}", response_model=DailyBriefing)
async def get_briefing(
    briefing_id: str,
    user: dict = Depends(get_current_user)
):
    """Get a specific briefing by ID."""
    try:
        r = await get_redis()
        data = await r.get(f"briefing:{user['user_id']}:{briefing_id}")
        if data:
            return DailyBriefing.model_validate_json(data)
    except Exception as e:
        logger.warning(f"Failed to get briefing: {e}")

    raise HTTPException(status_code=404, detail="Briefing not found")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host=settings.host, port=settings.port, reload=True)
