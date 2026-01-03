"""JARVIS User Profile Service - User data and preferences management."""

import logging
import uuid
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Optional
from functools import lru_cache

from fastapi import FastAPI, HTTPException, Depends, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, EmailStr, Field
from pydantic_settings import BaseSettings
from jose import jwt, JWTError
import asyncpg
import redis.asyncio as redis

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class Settings(BaseSettings):
    """Application settings."""
    service_name: str = "user-profile-service"
    host: str = "0.0.0.0"
    port: int = 8009
    debug: bool = False

    # Database
    database_url: str = "postgresql://postgres:postgres@localhost:5432/jarvis"

    # Redis
    redis_url: str = "redis://localhost:6379"
    cache_ttl: int = 3600  # 1 hour

    # JWT
    jwt_secret: str = "jarvis-secret-key"
    jwt_algorithm: str = "HS256"

    class Config:
        env_file = ".env"


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()


# Database connection pool
_db_pool: Optional[asyncpg.Pool] = None
_redis: Optional[redis.Redis] = None


async def get_db() -> asyncpg.Pool:
    global _db_pool
    if _db_pool is None:
        _db_pool = await asyncpg.create_pool(settings.database_url)
    return _db_pool


async def get_redis() -> redis.Redis:
    global _redis
    if _redis is None:
        _redis = redis.from_url(settings.redis_url)
    return _redis


# Models
class UserPreferences(BaseModel):
    """User preferences configuration."""
    preferred_title: str = "sir"
    timezone: str = "UTC"
    location: Optional[str] = None
    voice_id: str = "Brian"
    voice_rate: str = "medium"
    news_categories: list[str] = ["technology", "business", "science"]
    weather_units: str = "metric"
    briefing_time: str = "08:00"
    notifications_enabled: bool = True
    wake_word_enabled: bool = True


class UserProfile(BaseModel):
    """User profile model."""
    id: str
    email: str
    name: str
    preferences: UserPreferences
    created_at: datetime
    updated_at: datetime


class UserCreate(BaseModel):
    """Request model for creating a user."""
    email: EmailStr
    name: str
    password: str = Field(..., min_length=8)
    preferences: Optional[UserPreferences] = None


class UserUpdate(BaseModel):
    """Request model for updating a user."""
    name: Optional[str] = None
    preferences: Optional[UserPreferences] = None


class PreferencesUpdate(BaseModel):
    """Request model for updating preferences."""
    preferred_title: Optional[str] = None
    timezone: Optional[str] = None
    location: Optional[str] = None
    voice_id: Optional[str] = None
    voice_rate: Optional[str] = None
    news_categories: Optional[list[str]] = None
    weather_units: Optional[str] = None
    briefing_time: Optional[str] = None
    notifications_enabled: Optional[bool] = None
    wake_word_enabled: Optional[bool] = None


# Application lifecycle
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler."""
    logger.info(f"Starting {settings.service_name}")

    # Initialize database pool
    global _db_pool, _redis
    _db_pool = await asyncpg.create_pool(settings.database_url)
    _redis = redis.from_url(settings.redis_url)

    # Create tables if not exist
    async with _db_pool.acquire() as conn:
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                email VARCHAR(255) UNIQUE NOT NULL,
                name VARCHAR(255) NOT NULL,
                password_hash VARCHAR(255) NOT NULL,
                preferences JSONB DEFAULT '{}',
                created_at TIMESTAMP DEFAULT NOW(),
                updated_at TIMESTAMP DEFAULT NOW()
            )
        """)

    yield

    logger.info(f"Shutting down {settings.service_name}")
    if _db_pool:
        await _db_pool.close()
    if _redis:
        await _redis.close()


app = FastAPI(
    title="JARVIS User Profile Service",
    description="User data and preferences management",
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


def hash_password(password: str) -> str:
    """Hash a password (simplified - use bcrypt in production)."""
    import hashlib
    return hashlib.sha256(password.encode()).hexdigest()


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": settings.service_name,
        "timestamp": datetime.utcnow().isoformat()
    }


@app.post("/users", response_model=UserProfile)
async def create_user(
    user_data: UserCreate,
    db: asyncpg.Pool = Depends(get_db)
):
    """Create a new user."""
    preferences = user_data.preferences or UserPreferences()

    async with db.acquire() as conn:
        # Check if email exists
        existing = await conn.fetchrow(
            "SELECT id FROM users WHERE email = $1",
            user_data.email
        )
        if existing:
            raise HTTPException(status_code=400, detail="Email already registered")

        # Create user
        row = await conn.fetchrow(
            """
            INSERT INTO users (email, name, password_hash, preferences)
            VALUES ($1, $2, $3, $4)
            RETURNING id, email, name, preferences, created_at, updated_at
            """,
            user_data.email,
            user_data.name,
            hash_password(user_data.password),
            preferences.model_dump_json()
        )

    import json
    return UserProfile(
        id=str(row["id"]),
        email=row["email"],
        name=row["name"],
        preferences=UserPreferences(**json.loads(row["preferences"])),
        created_at=row["created_at"],
        updated_at=row["updated_at"]
    )


@app.get("/users/me", response_model=UserProfile)
async def get_current_user_profile(
    user: dict = Depends(get_current_user),
    db: asyncpg.Pool = Depends(get_db),
    redis_client: redis.Redis = Depends(get_redis)
):
    """Get the current user's profile."""
    user_id = user["user_id"]

    # Check cache
    cached = await redis_client.get(f"user:{user_id}")
    if cached:
        import json
        data = json.loads(cached)
        return UserProfile(**data)

    async with db.acquire() as conn:
        row = await conn.fetchrow(
            """
            SELECT id, email, name, preferences, created_at, updated_at
            FROM users WHERE id = $1
            """,
            uuid.UUID(user_id)
        )

    if not row:
        raise HTTPException(status_code=404, detail="User not found")

    import json
    profile = UserProfile(
        id=str(row["id"]),
        email=row["email"],
        name=row["name"],
        preferences=UserPreferences(**json.loads(row["preferences"])),
        created_at=row["created_at"],
        updated_at=row["updated_at"]
    )

    # Cache profile
    await redis_client.setex(
        f"user:{user_id}",
        settings.cache_ttl,
        profile.model_dump_json()
    )

    return profile


@app.put("/users/me", response_model=UserProfile)
async def update_current_user(
    update_data: UserUpdate,
    user: dict = Depends(get_current_user),
    db: asyncpg.Pool = Depends(get_db),
    redis_client: redis.Redis = Depends(get_redis)
):
    """Update the current user's profile."""
    user_id = user["user_id"]

    async with db.acquire() as conn:
        # Build update query dynamically
        updates = []
        values = []
        param_idx = 1

        if update_data.name:
            updates.append(f"name = ${param_idx}")
            values.append(update_data.name)
            param_idx += 1

        if update_data.preferences:
            updates.append(f"preferences = ${param_idx}")
            values.append(update_data.preferences.model_dump_json())
            param_idx += 1

        if not updates:
            raise HTTPException(status_code=400, detail="No updates provided")

        updates.append(f"updated_at = ${param_idx}")
        values.append(datetime.utcnow())
        param_idx += 1

        values.append(uuid.UUID(user_id))

        query = f"""
            UPDATE users SET {', '.join(updates)}
            WHERE id = ${param_idx}
            RETURNING id, email, name, preferences, created_at, updated_at
        """

        row = await conn.fetchrow(query, *values)

    if not row:
        raise HTTPException(status_code=404, detail="User not found")

    import json
    profile = UserProfile(
        id=str(row["id"]),
        email=row["email"],
        name=row["name"],
        preferences=UserPreferences(**json.loads(row["preferences"])),
        created_at=row["created_at"],
        updated_at=row["updated_at"]
    )

    # Invalidate cache
    await redis_client.delete(f"user:{user_id}")

    return profile


@app.get("/users/me/preferences", response_model=UserPreferences)
async def get_preferences(
    user: dict = Depends(get_current_user),
    db: asyncpg.Pool = Depends(get_db)
):
    """Get the current user's preferences."""
    user_id = user["user_id"]

    async with db.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT preferences FROM users WHERE id = $1",
            uuid.UUID(user_id)
        )

    if not row:
        raise HTTPException(status_code=404, detail="User not found")

    import json
    return UserPreferences(**json.loads(row["preferences"]))


@app.patch("/users/me/preferences", response_model=UserPreferences)
async def update_preferences(
    updates: PreferencesUpdate,
    user: dict = Depends(get_current_user),
    db: asyncpg.Pool = Depends(get_db),
    redis_client: redis.Redis = Depends(get_redis)
):
    """Update specific preferences."""
    user_id = user["user_id"]

    async with db.acquire() as conn:
        # Get current preferences
        row = await conn.fetchrow(
            "SELECT preferences FROM users WHERE id = $1",
            uuid.UUID(user_id)
        )

        if not row:
            raise HTTPException(status_code=404, detail="User not found")

        import json
        current = json.loads(row["preferences"])

        # Update only provided fields
        update_dict = updates.model_dump(exclude_unset=True)
        current.update(update_dict)

        # Save updated preferences
        await conn.execute(
            """
            UPDATE users SET preferences = $1, updated_at = $2
            WHERE id = $3
            """,
            json.dumps(current),
            datetime.utcnow(),
            uuid.UUID(user_id)
        )

    # Invalidate cache
    await redis_client.delete(f"user:{user_id}")

    return UserPreferences(**current)


@app.delete("/users/me")
async def delete_current_user(
    user: dict = Depends(get_current_user),
    db: asyncpg.Pool = Depends(get_db),
    redis_client: redis.Redis = Depends(get_redis)
):
    """Delete the current user's account."""
    user_id = user["user_id"]

    async with db.acquire() as conn:
        result = await conn.execute(
            "DELETE FROM users WHERE id = $1",
            uuid.UUID(user_id)
        )

    if result == "DELETE 0":
        raise HTTPException(status_code=404, detail="User not found")

    # Invalidate cache
    await redis_client.delete(f"user:{user_id}")

    return {"success": True, "message": "Account deleted"}


@app.get("/users/{user_id}", response_model=UserProfile)
async def get_user_by_id(
    user_id: str,
    current_user: dict = Depends(get_current_user),
    db: asyncpg.Pool = Depends(get_db)
):
    """Get a user by ID (admin only in production)."""
    async with db.acquire() as conn:
        row = await conn.fetchrow(
            """
            SELECT id, email, name, preferences, created_at, updated_at
            FROM users WHERE id = $1
            """,
            uuid.UUID(user_id)
        )

    if not row:
        raise HTTPException(status_code=404, detail="User not found")

    import json
    return UserProfile(
        id=str(row["id"]),
        email=row["email"],
        name=row["name"],
        preferences=UserPreferences(**json.loads(row["preferences"])),
        created_at=row["created_at"],
        updated_at=row["updated_at"]
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug
    )
