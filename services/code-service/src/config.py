"""Code service configuration."""

from functools import lru_cache
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Code service settings."""

    service_name: str = "code-service"
    host: str = "0.0.0.0"
    port: int = 8010
    debug: bool = False

    # Security
    jwt_secret: str = "your-secret-key"
    jwt_algorithm: str = "HS256"

    # File operations
    max_file_size_bytes: int = 10 * 1024 * 1024  # 10MB
    allowed_extensions: str = "*"  # Comma-separated or "*" for all
    workspace_root: str = ""  # Default workspace, empty = current dir

    # Git settings
    git_author_name: str = "JARVIS"
    git_author_email: str = "jarvis@local"

    # Search settings
    max_search_results: int = 100
    search_timeout_seconds: int = 30

    # Indexing
    index_on_startup: bool = False
    watch_for_changes: bool = True

    class Config:
        env_prefix = "CODE_"
        env_file = ".env"


@lru_cache
def get_settings() -> Settings:
    return Settings()
