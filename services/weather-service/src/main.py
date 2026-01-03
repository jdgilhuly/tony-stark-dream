"""JARVIS Weather Service - OpenWeatherMap Integration."""

import logging
import hashlib
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Optional
from functools import lru_cache

from fastapi import FastAPI, HTTPException, Depends, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings
import httpx
import redis.asyncio as redis
from jose import jwt, JWTError

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class Settings(BaseSettings):
    service_name: str = "weather-service"
    host: str = "0.0.0.0"
    port: int = 8003

    openweather_api_key: str = ""
    openweather_base_url: str = "https://api.openweathermap.org/data/2.5"

    redis_url: str = "redis://localhost:6379/0"
    cache_ttl_seconds: int = 1800  # 30 minutes

    jwt_secret: str = "development-secret-change-in-production"
    jwt_algorithm: str = "HS256"

    class Config:
        env_file = ".env"


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()


# Models
class CurrentWeather(BaseModel):
    temperature: float
    feels_like: float
    humidity: int
    pressure: int
    wind_speed: float
    wind_direction: int
    condition: str
    description: str
    icon: str
    visibility: int
    clouds: int


class ForecastItem(BaseModel):
    datetime: datetime
    temperature: float
    feels_like: float
    humidity: int
    condition: str
    description: str
    icon: str
    pop: float = Field(description="Probability of precipitation")
    wind_speed: float


class DailyForecast(BaseModel):
    date: datetime
    temp_min: float
    temp_max: float
    condition: str
    description: str
    icon: str
    pop: float
    humidity: int


class WeatherResponse(BaseModel):
    location: str
    country: str
    latitude: float
    longitude: float
    timezone_offset: int
    current: CurrentWeather
    hourly_forecast: list[ForecastItem] = []
    daily_forecast: list[DailyForecast] = []
    cached: bool = False
    cache_timestamp: Optional[datetime] = None


# Redis client
_redis: Optional[redis.Redis] = None


async def get_redis() -> redis.Redis:
    global _redis
    if _redis is None:
        _redis = redis.from_url(settings.redis_url, decode_responses=True)
    return _redis


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
    title="JARVIS Weather Service",
    description="Weather data from OpenWeatherMap with caching",
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


def cache_key(endpoint: str, **params) -> str:
    """Generate cache key from endpoint and params."""
    param_str = "&".join(f"{k}={v}" for k, v in sorted(params.items()))
    return f"weather:{endpoint}:{hashlib.md5(param_str.encode()).hexdigest()}"


async def get_cached(key: str) -> Optional[str]:
    """Get cached data."""
    try:
        r = await get_redis()
        return await r.get(key)
    except Exception as e:
        logger.warning(f"Cache read error: {e}")
        return None


async def set_cached(key: str, data: str, ttl: int = None):
    """Set cached data."""
    try:
        r = await get_redis()
        await r.set(key, data, ex=ttl or settings.cache_ttl_seconds)
    except Exception as e:
        logger.warning(f"Cache write error: {e}")


@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "service": settings.service_name,
        "timestamp": datetime.utcnow().isoformat()
    }


@app.get("/weather", response_model=WeatherResponse)
async def get_weather(
    lat: float = Query(..., ge=-90, le=90, description="Latitude"),
    lon: float = Query(..., ge=-180, le=180, description="Longitude"),
    units: str = Query("imperial", regex="^(metric|imperial|standard)$"),
    user: dict = Depends(get_current_user)
):
    """Get current weather and forecast for a location."""
    import json

    # Check cache
    key = cache_key("weather", lat=lat, lon=lon, units=units)
    cached_data = await get_cached(key)

    if cached_data:
        data = json.loads(cached_data)
        data["cached"] = True
        return WeatherResponse(**data)

    if not settings.openweather_api_key:
        raise HTTPException(status_code=503, detail="Weather API not configured")

    async with httpx.AsyncClient() as client:
        # Get current weather
        current_resp = await client.get(
            f"{settings.openweather_base_url}/weather",
            params={
                "lat": lat,
                "lon": lon,
                "units": units,
                "appid": settings.openweather_api_key
            }
        )

        if current_resp.status_code != 200:
            logger.error(f"OpenWeather API error: {current_resp.text}")
            raise HTTPException(status_code=502, detail="Weather API error")

        current_data = current_resp.json()

        # Get forecast
        forecast_resp = await client.get(
            f"{settings.openweather_base_url}/forecast",
            params={
                "lat": lat,
                "lon": lon,
                "units": units,
                "appid": settings.openweather_api_key
            }
        )

        forecast_data = forecast_resp.json() if forecast_resp.status_code == 200 else {"list": []}

    # Build response
    weather_cond = current_data["weather"][0] if current_data.get("weather") else {}

    current = CurrentWeather(
        temperature=current_data["main"]["temp"],
        feels_like=current_data["main"]["feels_like"],
        humidity=current_data["main"]["humidity"],
        pressure=current_data["main"]["pressure"],
        wind_speed=current_data["wind"]["speed"],
        wind_direction=current_data["wind"].get("deg", 0),
        condition=weather_cond.get("main", "Unknown"),
        description=weather_cond.get("description", ""),
        icon=weather_cond.get("icon", ""),
        visibility=current_data.get("visibility", 10000),
        clouds=current_data.get("clouds", {}).get("all", 0)
    )

    hourly = []
    for item in forecast_data.get("list", [])[:12]:
        cond = item["weather"][0] if item.get("weather") else {}
        hourly.append(ForecastItem(
            datetime=datetime.fromtimestamp(item["dt"]),
            temperature=item["main"]["temp"],
            feels_like=item["main"]["feels_like"],
            humidity=item["main"]["humidity"],
            condition=cond.get("main", ""),
            description=cond.get("description", ""),
            icon=cond.get("icon", ""),
            pop=item.get("pop", 0),
            wind_speed=item["wind"]["speed"]
        ))

    # Aggregate daily forecast
    daily_map = {}
    for item in forecast_data.get("list", []):
        date = datetime.fromtimestamp(item["dt"]).date()
        if date not in daily_map:
            daily_map[date] = {
                "temps": [],
                "pops": [],
                "humidity": [],
                "conditions": []
            }
        daily_map[date]["temps"].append(item["main"]["temp"])
        daily_map[date]["pops"].append(item.get("pop", 0))
        daily_map[date]["humidity"].append(item["main"]["humidity"])
        if item.get("weather"):
            daily_map[date]["conditions"].append(item["weather"][0])

    daily = []
    for date, data in sorted(daily_map.items())[:5]:
        cond = data["conditions"][0] if data["conditions"] else {}
        daily.append(DailyForecast(
            date=datetime.combine(date, datetime.min.time()),
            temp_min=min(data["temps"]),
            temp_max=max(data["temps"]),
            condition=cond.get("main", ""),
            description=cond.get("description", ""),
            icon=cond.get("icon", ""),
            pop=max(data["pops"]),
            humidity=sum(data["humidity"]) // len(data["humidity"])
        ))

    response = WeatherResponse(
        location=current_data.get("name", "Unknown"),
        country=current_data.get("sys", {}).get("country", ""),
        latitude=lat,
        longitude=lon,
        timezone_offset=current_data.get("timezone", 0),
        current=current,
        hourly_forecast=hourly,
        daily_forecast=daily,
        cached=False,
        cache_timestamp=datetime.utcnow()
    )

    # Cache the response
    await set_cached(key, response.model_dump_json())

    return response


@app.get("/weather/city")
async def get_weather_by_city(
    city: str = Query(..., min_length=1),
    country: Optional[str] = None,
    units: str = Query("imperial", regex="^(metric|imperial|standard)$"),
    user: dict = Depends(get_current_user)
):
    """Get weather by city name."""
    if not settings.openweather_api_key:
        raise HTTPException(status_code=503, detail="Weather API not configured")

    q = f"{city},{country}" if country else city

    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"{settings.openweather_base_url}/weather",
            params={
                "q": q,
                "units": units,
                "appid": settings.openweather_api_key
            }
        )

        if resp.status_code == 404:
            raise HTTPException(status_code=404, detail="City not found")
        if resp.status_code != 200:
            raise HTTPException(status_code=502, detail="Weather API error")

        data = resp.json()

    # Redirect to coordinate-based endpoint
    return await get_weather(
        lat=data["coord"]["lat"],
        lon=data["coord"]["lon"],
        units=units,
        user=user
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host=settings.host, port=settings.port, reload=True)
