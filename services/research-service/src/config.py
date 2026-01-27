"""Research service configuration."""

from functools import lru_cache
from typing import List, Optional
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Research service settings."""

    service_name: str = "research-service"
    host: str = "0.0.0.0"
    port: int = 8014
    debug: bool = False

    # Security
    jwt_secret: str = "your-secret-key"
    jwt_algorithm: str = "HS256"

    # Search settings
    default_search_engine: str = "duckduckgo"  # duckduckgo, brave, serpapi
    max_search_results: int = 10
    search_timeout: int = 30

    # API keys for premium search (optional)
    brave_api_key: str = ""
    serpapi_key: str = ""

    # Content extraction
    extraction_timeout: int = 30
    max_content_length: int = 50000  # characters
    enable_javascript_rendering: bool = False

    # Caching
    enable_cache: bool = True
    cache_dir: str = "./data/research_cache"
    cache_ttl_seconds: int = 3600  # 1 hour
    search_cache_ttl: int = 1800  # 30 minutes

    # Rate limiting
    requests_per_minute: int = 30

    # Content synthesis
    summarization_model: str = "claude-haiku"  # For summarizing content
    max_summary_length: int = 500

    # Knowledge base
    enable_knowledge_base: bool = True
    knowledge_db_path: str = "./data/knowledge.db"

    class Config:
        env_prefix = "RESEARCH_"
        env_file = ".env"


@lru_cache
def get_settings() -> Settings:
    return Settings()
