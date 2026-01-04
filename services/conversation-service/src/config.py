from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # Service
    service_name: str = "conversation-service"
    host: str = "0.0.0.0"
    port: int = 8001
    debug: bool = False

    # AWS (for Bedrock fallback)
    aws_region: str = "us-east-1"
    aws_access_key_id: str | None = None
    aws_secret_access_key: str | None = None

    # OpenAI API (preferred)
    openai_api_key: str | None = None
    openai_model: str = "gpt-4o"
    openai_max_tokens: int = 4096

    # AWS Bedrock (fallback)
    bedrock_model_id: str = "anthropic.claude-3-5-sonnet-20241022-v2:0"
    bedrock_max_tokens: int = 4096

    # LLM Provider: "openai" or "bedrock"
    llm_provider: str = "openai"

    # Database
    database_url: str = "postgresql://jarvis:jarvis@localhost:5432/jarvis"

    # Redis
    redis_url: str = "redis://localhost:6379/0"
    redis_ttl_short: int = 86400  # 24 hours for short-term memory
    redis_ttl_working: int = 604800  # 7 days for working memory

    # JWT
    jwt_secret: str = "development-secret-change-in-production"
    jwt_algorithm: str = "HS256"

    # Conversation
    max_context_messages: int = 20
    max_context_tokens: int = 8000

    # Service URLs for integrations
    weather_service_url: str = "http://localhost:8003"
    news_service_url: str = "http://localhost:8004"
    briefing_service_url: str = "http://localhost:8005"
    calendar_service_url: str = "http://localhost:8006"
    task_execution_url: str = "http://localhost:8007"
    notification_service_url: str = "http://localhost:8008"

    class Config:
        env_file = "../../.env"  # Project root .env file
        env_file_encoding = "utf-8"
        extra = "ignore"  # Ignore extra env vars not defined in Settings


@lru_cache
def get_settings() -> Settings:
    return Settings()
