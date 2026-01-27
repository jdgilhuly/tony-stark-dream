"""Claude service configuration."""

from functools import lru_cache
from typing import List, Optional
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Claude service settings."""

    service_name: str = "claude-service"
    host: str = "0.0.0.0"
    port: int = 8013
    debug: bool = False

    # Security
    jwt_secret: str = "your-secret-key"
    jwt_algorithm: str = "HS256"

    # Claude API
    anthropic_api_key: str = ""
    claude_model: str = "claude-sonnet-4-20250514"
    claude_max_tokens: int = 8192
    claude_temperature: float = 0.7

    # Fallback to Ollama
    enable_ollama_fallback: bool = True
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "llama3.2"

    # Context management
    max_context_tokens: int = 100000
    context_buffer_tokens: int = 4000  # Reserve for response

    # Rate limiting
    requests_per_minute: int = 60
    tokens_per_minute: int = 100000

    # Retry settings
    max_retries: int = 3
    retry_delay: float = 1.0
    retry_multiplier: float = 2.0

    # Tool use
    max_tool_iterations: int = 10
    tool_timeout: int = 30000  # milliseconds

    # Streaming
    stream_chunk_size: int = 100  # characters

    # Caching
    enable_response_cache: bool = True
    cache_ttl_seconds: int = 3600

    class Config:
        env_prefix = "CLAUDE_"
        env_file = ".env"


@lru_cache
def get_settings() -> Settings:
    return Settings()
