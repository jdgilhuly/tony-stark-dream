"""Browser service configuration."""

from functools import lru_cache
from typing import List, Optional
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Browser service settings."""

    service_name: str = "browser-service"
    host: str = "0.0.0.0"
    port: int = 8012
    debug: bool = False

    # Security
    jwt_secret: str = "your-secret-key"
    jwt_algorithm: str = "HS256"

    # Browser settings
    browser_type: str = "chromium"  # chromium, firefox, webkit
    headless: bool = True
    default_timeout: int = 30000  # milliseconds
    default_viewport_width: int = 1920
    default_viewport_height: int = 1080

    # Navigation
    default_wait_until: str = "domcontentloaded"  # load, domcontentloaded, networkidle
    navigation_timeout: int = 30000

    # Screenshots
    screenshot_dir: str = "./data/screenshots"
    screenshot_format: str = "png"  # png, jpeg
    screenshot_quality: int = 90  # for jpeg

    # PDF
    pdf_dir: str = "./data/pdfs"

    # Session management
    max_sessions_per_user: int = 5
    session_timeout: int = 3600  # seconds

    # Content extraction
    max_content_length: int = 100000  # characters
    enable_javascript: bool = True

    # Security restrictions
    blocked_domains: List[str] = []
    allowed_domains: Optional[List[str]] = None  # None = allow all

    # Resource limits
    max_concurrent_pages: int = 10
    max_request_size: int = 10 * 1024 * 1024  # 10MB

    class Config:
        env_prefix = "BROWSER_"
        env_file = ".env"


@lru_cache
def get_settings() -> Settings:
    return Settings()
