"""Orchestration service configuration."""

from functools import lru_cache
from typing import Dict, Optional
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Orchestration service settings."""

    service_name: str = "orchestration-service"
    host: str = "0.0.0.0"
    port: int = 8016
    debug: bool = False

    # Security
    jwt_secret: str = "your-secret-key"
    jwt_algorithm: str = "HS256"

    # Service URLs
    claude_service_url: str = "http://localhost:8013"
    code_service_url: str = "http://localhost:8010"
    browser_service_url: str = "http://localhost:8012"
    memory_service_url: str = "http://localhost:8011"
    research_service_url: str = "http://localhost:8014"
    github_service_url: str = "http://localhost:8015"

    # Redis (optional, for distributed state)
    redis_url: Optional[str] = None

    # Task execution
    max_parallel_tasks: int = 5
    task_timeout: int = 300  # seconds
    max_retries: int = 3
    retry_delay: float = 1.0

    # Workflow
    max_workflow_steps: int = 50
    step_timeout: int = 120  # seconds

    # Agent selection
    agent_confidence_threshold: float = 0.6
    default_agent: str = "general"

    class Config:
        env_prefix = "ORCHESTRATION_"
        env_file = ".env"


@lru_cache
def get_settings() -> Settings:
    return Settings()
