"""Learning service configuration."""

from functools import lru_cache
from typing import Optional
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Learning service settings."""

    service_name: str = "learning-service"
    host: str = "0.0.0.0"
    port: int = 8017
    debug: bool = False

    # Security
    jwt_secret: str = "your-secret-key"
    jwt_algorithm: str = "HS256"

    # Service URLs
    memory_service_url: str = "http://localhost:8011"
    claude_service_url: str = "http://localhost:8013"
    conversation_service_url: str = "http://localhost:8001"

    # Database
    db_path: str = "./data/learning.db"

    # Learning settings
    feedback_threshold: float = 0.7  # Min confidence for auto-learning
    reflection_interval_hours: int = 24  # Hours between reflections
    pattern_min_occurrences: int = 3  # Min occurrences to form a pattern
    max_patterns_per_category: int = 100

    # Metrics
    metrics_retention_days: int = 30
    enable_detailed_logging: bool = True

    class Config:
        env_prefix = "LEARNING_"
        env_file = ".env"


@lru_cache
def get_settings() -> Settings:
    return Settings()
