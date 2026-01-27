"""GitHub service configuration."""

from functools import lru_cache
from typing import List, Optional
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """GitHub service settings."""

    service_name: str = "github-service"
    host: str = "0.0.0.0"
    port: int = 8015
    debug: bool = False

    # Security
    jwt_secret: str = "your-secret-key"
    jwt_algorithm: str = "HS256"

    # GitHub API
    github_token: str = ""
    github_app_id: Optional[str] = None
    github_app_private_key: Optional[str] = None
    github_webhook_secret: Optional[str] = None

    # Git settings
    git_clone_dir: str = "./data/repos"
    git_user_name: str = "JARVIS"
    git_user_email: str = "jarvis@example.com"

    # Rate limiting
    requests_per_minute: int = 60

    # Caching
    enable_cache: bool = True
    cache_ttl_seconds: int = 300

    # Webhook settings
    webhook_timeout: int = 10

    class Config:
        env_prefix = "GITHUB_"
        env_file = ".env"


@lru_cache
def get_settings() -> Settings:
    return Settings()
